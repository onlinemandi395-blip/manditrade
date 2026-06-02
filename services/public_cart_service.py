from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class PublicCartService:
    def __init__(self, public_buyer_service, product_catalog_service, safe_drive_write_service, json_service, id_allocator_service, cart_service=None) -> None:
        self.public_buyer_service = public_buyer_service
        self.product_catalog_service = product_catalog_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.cart_service = cart_service

    def _default_cart(self, public_buyer_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "cart_id": self.id_allocator_service.allocate("cart"),
            "public_buyer_id": public_buyer_id,
            "items": [],
            "subtotal": 0.0,
            "payment_required": 0.0,
            "status": "OPEN",
            "assigned_seller_manufacturer_id": "",
            "updated_at": datetime.now(UTC).isoformat(),
        }

    def get_cart(self, public_buyer_id: str) -> dict[str, Any]:
        if self.cart_service:
            return self.cart_service.get_cart("public_buyer", public_buyer_id, "MARKETPLACE")
        path = self.public_buyer_service.cart_path(public_buyer_id)
        if not path.exists():
            cart = self._default_cart(public_buyer_id)
            self.safe_drive_write_service.replace_document(path, cart)
            return cart
        return self.json_service.read_json(path, self._default_cart(public_buyer_id))

    def add_item(self, public_buyer_id: str, *, product_id: str, qty: int) -> dict[str, Any]:
        if self.cart_service:
            return self.cart_service.add_item("public_buyer", public_buyer_id, cart_type="MARKETPLACE", item_id=product_id, qty=qty)
        product = self.product_catalog_service.get_product(product_id)
        self._ensure_public_product(product)
        requested_qty = max(int(qty or 0), int(product.get("minimum_order_qty", 1) or 1))
        seller_id = self._seller_of(product)
        if not seller_id:
            raise ValueError("Public product is missing a public seller assignment.")
        path = self.public_buyer_service.cart_path(public_buyer_id)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload = payload or self._default_cart(public_buyer_id)
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("items", [])
            current_seller = payload.get("assigned_seller_manufacturer_id", "")
            if current_seller and current_seller != seller_id and payload.get("items"):
                raise ValueError("Multi-seller public checkout is blocked in the current marketplace flow.")
            payload["assigned_seller_manufacturer_id"] = seller_id
            item = next((entry for entry in payload["items"] if entry.get("product_id") == product_id), None)
            marketplace_price = float(product.get("approved_marketplace_price") or product.get("marketplace_price") or product.get("approved_client_price") or product.get("client_price") or product.get("approved_mrp") or product.get("mrp") or 0)
            mandi_price = float(product.get("approved_mandi_price") or product.get("mandi_price") or 0)
            if item:
                item["qty"] = requested_qty
                item["marketplace_price"] = marketplace_price
                item["price"] = marketplace_price
                item["mrp"] = marketplace_price
                item["mandi_price"] = mandi_price
                item["unit"] = product.get("unit", "unit")
            else:
                payload["items"].append(
                    {
                        "product_id": product_id,
                        "product_name": product.get("name", product_id),
                        "qty": requested_qty,
                        "unit": product.get("unit", "unit"),
                        "marketplace_price": marketplace_price,
                        "price": marketplace_price,
                        "mrp": marketplace_price,
                        "mandi_price": mandi_price,
                        "public_seller_manufacturer_id": seller_id,
                    }
                )
            self._recompute(payload)
            payload["updated_at"] = datetime.now(UTC).isoformat()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return self.get_cart(public_buyer_id)

    def clear_cart(self, public_buyer_id: str) -> dict[str, Any]:
        if self.cart_service:
            return self.cart_service.clear_cart("public_buyer", public_buyer_id, cart_type="MARKETPLACE")
        cart = self._default_cart(public_buyer_id)
        self.safe_drive_write_service.replace_document(self.public_buyer_service.cart_path(public_buyer_id), cart)
        return cart

    def _ensure_public_product(self, product: dict[str, Any]) -> None:
        if product.get("status") != "ACTIVE":
            raise ValueError("Only ACTIVE products can be purchased in the public marketplace.")
        if (product.get("approved_visibility") or "").strip().upper() != "PUBLIC":
            raise ValueError("Only PUBLIC products can be purchased in the public marketplace.")
        if not bool(product.get("available_for_public_sale", False)):
            raise ValueError("This product is not available for public sale.")

    def _seller_of(self, product: dict[str, Any]) -> str:
        return (
            str(product.get("public_seller_manufacturer_id") or "").strip()
            or str(product.get("created_by_manufacturer_id") or product.get("created_by") or "").strip()
        )

    def _recompute(self, payload: dict[str, Any]) -> None:
        subtotal = sum(float(item.get("marketplace_price", item.get("mrp", 0))) * int(item.get("qty", 0)) for item in payload.get("items", []))
        payload["subtotal"] = subtotal
        payload["payment_required"] = subtotal
        payload["status"] = "OPEN"
