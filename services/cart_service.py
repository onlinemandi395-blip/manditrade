from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class CartService:
    VALID_CART_TYPES = {"MARKETPLACE", "MANDIPLACE", "SUTA_MANDI", "RAW_MATERIAL"}

    def __init__(
        self,
        *,
        carts_root: Path,
        safe_drive_write_service,
        json_service,
        id_allocator_service,
        product_catalog_service,
        governance_service,
        procurement_transaction_service,
        public_order_service=None,
    ) -> None:
        self.carts_root = carts_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.product_catalog_service = product_catalog_service
        self.governance_service = governance_service
        self.procurement_transaction_service = procurement_transaction_service
        self.public_order_service = public_order_service

    def cart_path(self, owner_role: str, owner_id: str, cart_type: str) -> Path:
        return self.carts_root / owner_role / owner_id / f"{cart_type.lower()}.json"

    def get_cart(self, owner_role: str, owner_id: str, cart_type: str) -> dict[str, Any]:
        normalized_type = self._cart_type(cart_type)
        path = self.cart_path(owner_role, owner_id, normalized_type)
        if not path.exists():
            cart = self._default_cart(owner_role, owner_id, normalized_type)
            self.safe_drive_write_service.replace_document(path, cart)
            return cart
        return self.json_service.read_json(path, self._default_cart(owner_role, owner_id, normalized_type))

    def add_item(self, owner_role: str, owner_id: str, *, cart_type: str, item_id: str, qty: int, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized_type = self._cart_type(cart_type)
        path = self.cart_path(owner_role, owner_id, normalized_type)
        requested_qty = max(int(qty or 0), 1)
        item_payload = self._resolve_item_payload(owner_role, normalized_type, item_id, requested_qty, metadata or {})

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload = payload or self._default_cart(owner_role, owner_id, normalized_type)
            payload.setdefault("items", [])
            existing = next((item for item in payload["items"] if item.get("item_id") == item_payload["item_id"]), None)
            if existing:
                existing.update(item_payload)
            else:
                payload["items"].append(item_payload)
            self._recompute(payload)
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return self.get_cart(owner_role, owner_id, normalized_type)

    def update_qty(self, owner_role: str, owner_id: str, *, cart_type: str, item_id: str, qty: int) -> dict[str, Any]:
        normalized_type = self._cart_type(cart_type)
        path = self.cart_path(owner_role, owner_id, normalized_type)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("item_id") == item_id:
                    item["qty"] = max(int(qty or 0), 1)
                    self._recompute(payload)
                    payload["updated_at"] = datetime.now(UTC).isoformat()
                    return payload
            raise ValueError(f"Cart item not found: {item_id}")

        self.safe_drive_write_service.mutate_json(path, mutator)
        return self.get_cart(owner_role, owner_id, normalized_type)

    def remove_item(self, owner_role: str, owner_id: str, *, cart_type: str, item_id: str) -> dict[str, Any]:
        normalized_type = self._cart_type(cart_type)
        path = self.cart_path(owner_role, owner_id, normalized_type)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["items"] = [item for item in payload.get("items", []) if item.get("item_id") != item_id]
            self._recompute(payload)
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return self.get_cart(owner_role, owner_id, normalized_type)

    def clear_cart(self, owner_role: str, owner_id: str, *, cart_type: str) -> dict[str, Any]:
        normalized_type = self._cart_type(cart_type)
        cart = self._default_cart(owner_role, owner_id, normalized_type)
        self.safe_drive_write_service.replace_document(self.cart_path(owner_role, owner_id, normalized_type), cart)
        return cart

    def checkout(self, owner_role: str, owner_id: str, *, cart_type: str, checkout_context: dict[str, Any]) -> Any:
        normalized_type = self._cart_type(cart_type)
        cart = self.get_cart(owner_role, owner_id, normalized_type)
        items = list(cart.get("items", []))
        if not items:
            raise ValueError("Cart is empty.")
        if normalized_type == "MARKETPLACE":
            if owner_role != "public_buyer" or not self.public_order_service:
                raise PermissionError("Marketplace checkout is available only for public buyers.")
            return self.public_order_service.create_order_from_cart(owner_id)
        if owner_role not in {"manufacturer", "admin_as_manufacturer"}:
            raise PermissionError("Only manufacturers can request mandi or suta supplies.")
        created_orders = []
        manufacturer_code = str(checkout_context.get("manufacturer_code") or "").strip()
        requester_email = str(checkout_context.get("requester_email") or "").strip()
        if not manufacturer_code or not requester_email:
            raise ValueError("Manufacturer checkout requires manufacturer_code and requester_email.")
        for item in items:
            created_orders.append(
                self.procurement_transaction_service.create_supply_request(
                    manufacturer_code=manufacturer_code,
                    raw_material_id=item["item_id"],
                    qty=float(item.get("qty", 0) or 0),
                    unit=str(item.get("unit", "kg")),
                    requested_by=requester_email,
                    notes=str(item.get("notes", "")),
                )
            )
        self.clear_cart(owner_role, owner_id, cart_type=normalized_type)
        return created_orders

    def _resolve_item_payload(self, owner_role: str, cart_type: str, item_id: str, qty: int, metadata: dict[str, Any]) -> dict[str, Any]:
        if cart_type == "MARKETPLACE":
            if owner_role != "public_buyer":
                raise PermissionError("Only public buyers can add marketplace items to cart.")
            product = self.product_catalog_service.get_product(item_id)
            minimum = max(int(product.get("minimum_order_qty", 1) or 1), 1)
            requested_qty = max(qty, minimum)
            seller_id = str(product.get("public_seller_manufacturer_id") or product.get("created_by_manufacturer_id") or product.get("created_by") or "").strip()
            if not seller_id:
                raise ValueError("Marketplace product is missing a seller assignment.")
            return {
                "item_id": item_id,
                "product_id": item_id,
                "product_name": product.get("name", item_id),
                "qty": requested_qty,
                "unit": product.get("unit", "unit"),
                "price": float(product.get("marketplace_price", product.get("approved_marketplace_price", product.get("price", 0))) or 0),
                "marketplace_price": float(product.get("marketplace_price", product.get("approved_marketplace_price", product.get("price", 0))) or 0),
                "assigned_seller_manufacturer_id": seller_id,
                "image_url": product.get("image_url", ""),
                "thumbnail_url": product.get("thumbnail_url", ""),
            }
        material = self.governance_service.list_raw_materials()
        raw = next((item for item in material if item.get("raw_material_id") == item_id), None)
        if raw is None:
            raise ValueError(f"Raw material not found: {item_id}")
        return {
            "item_id": item_id,
            "raw_material_id": item_id,
            "name": raw.get("name", item_id),
            "qty": max(qty, 1),
            "unit": raw.get("unit", "kg"),
            "price": float(raw.get("supply_price", 0) or 0),
            "supply_price": float(raw.get("supply_price", 0) or 0),
            "mahajan_id": raw.get("mahajan_id", ""),
            "category": raw.get("category", "RAW_MATERIAL"),
            "notes": str(metadata.get("notes", "")),
            "image_url": raw.get("image_url", ""),
            "thumbnail_url": raw.get("thumbnail_url", ""),
        }

    def _recompute(self, payload: dict[str, Any]) -> None:
        subtotal = round(sum(float(item.get("price", 0) or 0) * float(item.get("qty", 0) or 0) for item in payload.get("items", [])), 2)
        payload["subtotal"] = subtotal
        payload["status"] = "OPEN"
        if payload.get("cart_type") == "MARKETPLACE":
            seller_ids = {str(item.get("assigned_seller_manufacturer_id", "")).strip() for item in payload.get("items", []) if item.get("assigned_seller_manufacturer_id")}
            if len(seller_ids) > 1:
                raise ValueError("Multi-seller public checkout is blocked in the current marketplace flow.")
            payload["assigned_seller_manufacturer_id"] = next(iter(seller_ids), "")
            payload["payment_required"] = subtotal

    def _default_cart(self, owner_role: str, owner_id: str, cart_type: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "cart_id": self.id_allocator_service.allocate("cart"),
            "owner_role": owner_role,
            "owner_id": owner_id,
            "cart_type": cart_type,
            "items": [],
            "subtotal": 0.0,
            "status": "OPEN",
            "payment_required": 0.0,
            "assigned_seller_manufacturer_id": "",
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def _cart_type(self, cart_type: str) -> str:
        normalized = str(cart_type or "").strip().upper()
        if normalized not in self.VALID_CART_TYPES:
            raise ValueError(f"Unsupported cart type: {cart_type}")
        return normalized
