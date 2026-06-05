from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class ProcurementContext:
    transaction_id: str
    state: str = "PENDING"
    affected_files: list[str] = field(default_factory=list)
    backup_targets: list[Path] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    error_message: str = ""


class ProcurementTransactionService:
    def __init__(
        self,
        drive_service,
        safe_drive_write_service,
        rollback_service,
        gmail_service,
        audit_service,
        logging_service,
        transactions_root: Path,
        event_dispatcher,
        id_allocator_service,
        dual_inventory_service,
        trade_confirmation_service,
        ledger_service,
        notification_center_service,
        domain_paths_service,
        governance_service=None,
        pricing_service=None,
        event_notification_service=None,
        product_catalog_service=None,
        settlement_service=None,
        invoice_service=None,
    ) -> None:
        self.drive_service = drive_service
        self.safe_drive_write_service = safe_drive_write_service
        self.rollback_service = rollback_service
        self.gmail_service = gmail_service
        self.audit_service = audit_service
        self.logging_service = logging_service
        self.transactions_root = transactions_root
        self.event_dispatcher = event_dispatcher
        self.id_allocator_service = id_allocator_service
        self.dual_inventory_service = dual_inventory_service
        self.trade_confirmation_service = trade_confirmation_service
        self.ledger_service = ledger_service
        self.notification_center_service = notification_center_service
        self.domain_paths = domain_paths_service
        self.governance_service = governance_service
        self.pricing_service = pricing_service
        self.event_notification_service = event_notification_service
        self.product_catalog_service = product_catalog_service
        self.settlement_service = settlement_service
        self.invoice_service = invoice_service

    def _inventory_service(self):
        return getattr(self.dual_inventory_service, "inventory_service", None)

    def _raw_material_record(self, raw_material_id: str) -> dict[str, Any]:
        if not self.governance_service:
            return {}
        material_key = str(raw_material_id or "").strip().upper()
        return next((item for item in self.governance_service.list_raw_materials() if item.get("raw_material_id") == material_key), {})

    def _raw_material_network(self, raw_material_id: str) -> str:
        material = self._raw_material_record(raw_material_id)
        category = str(material.get("category", "")).strip().upper()
        return "SUTA_MANDI" if category == "SUTA" else "RAW_MATERIALS"

    def _reserve_supply_inventory(self, order: dict[str, Any], *, actor_email: str) -> None:
        inventory_service = self._inventory_service()
        if not inventory_service:
            return
        mahajan_id = str(order.get("mahajan_id", "")).strip().upper()
        raw_material_id = str(order.get("raw_material_id", "")).strip().upper()
        if not mahajan_id or not raw_material_id:
            return
        network = self._raw_material_network(raw_material_id)
        item_type = "SUTA" if network == "SUTA_MANDI" else "RAW_MATERIAL"
        inventory_service.reserve_order_items(
            owner_role="mahajan",
            owner_id=mahajan_id,
            item_type=item_type,
            network=network,
            items=[{"raw_material_id": raw_material_id, "qty": order.get("qty", 0)}],
            related_order_id=str(order.get("mandi_order_id", "")),
            created_by=actor_email,
            note="Supply order reserved stock",
        )

    def _release_supply_inventory(self, order: dict[str, Any], *, actor_email: str, note: str) -> None:
        inventory_service = self._inventory_service()
        if not inventory_service:
            return
        mahajan_id = str(order.get("mahajan_id", "")).strip().upper()
        raw_material_id = str(order.get("raw_material_id", "")).strip().upper()
        if not mahajan_id or not raw_material_id:
            return
        network = self._raw_material_network(raw_material_id)
        item_type = "SUTA" if network == "SUTA_MANDI" else "RAW_MATERIAL"
        inventory_service.release_order_reservations(
            owner_role="mahajan",
            owner_id=mahajan_id,
            item_type=item_type,
            network=network,
            items=[{"raw_material_id": raw_material_id, "qty": order.get("qty", 0)}],
            related_order_id=str(order.get("mandi_order_id", "")),
            created_by=actor_email,
            note=note,
        )

    def _mark_supply_inventory_dispatched(self, order: dict[str, Any], *, actor_email: str) -> None:
        inventory_service = self._inventory_service()
        if not inventory_service:
            return
        mahajan_id = str(order.get("mahajan_id", "")).strip().upper()
        raw_material_id = str(order.get("raw_material_id", "")).strip().upper()
        if not mahajan_id or not raw_material_id:
            return
        network = self._raw_material_network(raw_material_id)
        item_type = "SUTA" if network == "SUTA_MANDI" else "RAW_MATERIAL"
        record = inventory_service.get_inventory_by_keys(
            owner_role="mahajan",
            owner_id=mahajan_id,
            item_type=item_type,
            item_id=raw_material_id,
            network=network,
        )
        if not record:
            return
        inventory_service.mark_dispatched(
            inventory_id=record["inventory_id"],
            qty=int(float(order.get("qty", 0) or 0)),
            related_order_id=str(order.get("mandi_order_id", "")),
            note="Supply order dispatched",
            created_by=actor_email,
        )

    def _complete_supply_inventory(self, order: dict[str, Any], *, actor_email: str) -> None:
        inventory_service = self._inventory_service()
        if not inventory_service:
            return
        mahajan_id = str(order.get("mahajan_id", "")).strip().upper()
        raw_material_id = str(order.get("raw_material_id", "")).strip().upper()
        if not mahajan_id or not raw_material_id:
            return
        network = self._raw_material_network(raw_material_id)
        item_type = "SUTA" if network == "SUTA_MANDI" else "RAW_MATERIAL"
        inventory_service.confirm_order_items(
            owner_role="mahajan",
            owner_id=mahajan_id,
            item_type=item_type,
            network=network,
            items=[{"raw_material_id": raw_material_id, "qty": order.get("qty", 0)}],
            related_order_id=str(order.get("mandi_order_id", "")),
            created_by=actor_email,
            note="Supply order received",
        )
        record = inventory_service.get_inventory_by_keys(
            owner_role="mahajan",
            owner_id=mahajan_id,
            item_type=item_type,
            item_id=raw_material_id,
            network=network,
        )
        if record:
            inventory_service.mark_received(
                inventory_id=record["inventory_id"],
                qty=int(float(order.get("qty", 0) or 0)),
                related_order_id=str(order.get("mandi_order_id", "")),
                note="Supply order received",
                created_by=actor_email,
            )

    def _default_logistics(self) -> dict[str, Any]:
        return {
            "logistics_owner": "platform_admin",
            "delivery_status": "",
            "transport_mode": "",
            "driver_name": "",
            "driver_mobile": "",
            "vehicle_number": "",
            "dispatch_time": "",
            "expected_delivery": "",
            "dispatch_note": "",
            "delivery_note": "",
            "proof_url": "",
            "proof_image_url": "",
            "delivered_at": "",
        }

    def _default_packaging(self) -> dict[str, Any]:
        return {
            "packaging_service_id": "",
            "packaging_name": "",
            "qty": 0,
            "unit_price": 0.0,
            "total_packaging_cost": 0.0,
            "packaging_note": "",
        }

    def _default_courier(self) -> dict[str, Any]:
        return {
            "courier_service_id": "",
            "provider_name": "",
            "pickup_location": "",
            "delivery_location": "",
            "distance_km": 0.0,
            "weight_kg": 0.0,
            "courier_cost": 0.0,
            "tracking_reference": "",
            "driver_name": "",
            "driver_mobile": "",
            "vehicle_number": "",
            "status": "",
        }

    def _validate_available_items(self, available_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in available_items:
            qty = int(item.get("qty", 0) or 0)
            unit_price = float(item.get("offered_unit_price", item.get("unit_price", 0)) or 0)
            if qty <= 0:
                raise ValueError("Sourcing response quantity must be greater than zero.")
            if unit_price <= 0:
                raise ValueError("Sourcing response offered unit price is required and must be greater than zero.")
            normalized.append(
                {
                    **item,
                    "qty": qty,
                    "offered_unit_price": round(unit_price, 2),
                    "total_price": round(qty * unit_price, 2),
                }
            )
        return normalized

    def _journal_path(self, transaction_id: str) -> Path:
        return self.transactions_root / f"{transaction_id}.json"

    def _write_journal(self, context: ProcurementContext) -> None:
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        self._journal_path(context.transaction_id).write_text(
            json.dumps(
                {
                    "transaction_id": context.transaction_id,
                    "state": context.state,
                    "affected_files": context.affected_files,
                    "backup_targets": [str(item) for item in context.backup_targets],
                    "created_at": context.created_at,
                    "error_message": context.error_message,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _register_target(self, context: ProcurementContext, target: Path) -> None:
        if target not in context.backup_targets:
            context.backup_targets.append(target)
            context.affected_files.append(str(target))
            self.safe_drive_write_service.backup_file(target)

    def _rfq_doc(self, manufacturer_code: str) -> dict[str, Any]:
        return self.drive_service.json_service.read_json(self.domain_paths.rfq_path(manufacturer_code), {"schema_version": "2.0", "rfqs": [], "responses": []})

    def create_rfq_from_shortage(self, *, manufacturer_code: str, items: list[dict[str, Any]], trade_terms: dict[str, Any]) -> dict[str, Any]:
        path = self.domain_paths.rfq_path(manufacturer_code)
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, {"schema_version": "2.0", "rfqs": [], "responses": []})
        rfq = {
            "rfq_id": self.id_allocator_service.allocate("rfq"),
            "buyer_manufacturer_id": manufacturer_code,
            "items": items,
            "trade_terms": trade_terms,
            "status": "OPEN",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.safe_drive_write_service.append_record(path, "rfqs", rfq)
        return rfq

    def list_requests(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return self._rfq_doc(manufacturer_code).get("rfqs", [])

    def list_responses(self, manufacturer_code: str) -> list[dict[str, Any]]:
        return self._rfq_doc(manufacturer_code).get("responses", [])

    def list_supply_orders(self, *, manufacturer_code: str | None = None, mahajan_id: str | None = None) -> list[dict[str, Any]]:
        if not self.governance_service:
            return []
        orders = self.governance_service.list_supply_orders()
        if manufacturer_code:
            orders = [item for item in orders if item.get("manufacturer_id") == manufacturer_code]
        if mahajan_id:
            orders = [item for item in orders if item.get("mahajan_id") == mahajan_id]
        return orders

    def list_mandiplace_orders(
        self,
        *,
        requesting_manufacturer_id: str | None = None,
        supplier_manufacturer_id: str | None = None,
        manufacturer_code: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.governance_service:
            return []
        orders = self.governance_service.list_mandiplace_orders()
        if requesting_manufacturer_id:
            orders = [item for item in orders if item.get("requesting_manufacturer_id") == requesting_manufacturer_id]
        if supplier_manufacturer_id:
            orders = [item for item in orders if item.get("supplier_manufacturer_id") == supplier_manufacturer_id]
        if manufacturer_code:
            orders = [
                item
                for item in orders
                if item.get("requesting_manufacturer_id") == manufacturer_code or item.get("supplier_manufacturer_id") == manufacturer_code
            ]
        return orders

    def create_mandiplace_request(
        self,
        *,
        requesting_manufacturer_id: str,
        items: list[dict[str, Any]],
        requested_by: str,
        notes: str = "",
    ) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for MandiPlace requests.")
        normalized_items: list[dict[str, Any]] = []
        for item in items:
            qty = float(item.get("qty", 0) or 0)
            if qty <= 0:
                raise ValueError("Requested quantity must be greater than zero.")
            normalized_items.append(
                {
                    "product_id": str(item.get("product_id") or "").strip(),
                    "name": str(item.get("name") or item.get("product_name") or "").strip(),
                    "qty": qty,
                    "unit": str(item.get("unit") or "unit").strip(),
                    "requested_location": str(item.get("requested_location") or "").strip(),
                    "required_by_date": str(item.get("required_by_date") or "").strip(),
                }
            )
        if not normalized_items:
            raise ValueError("At least one MandiPlace item is required.")
        qty_total = sum(float(item.get("qty", 0) or 0) for item in normalized_items)
        order = {
            "mandiplace_order_id": self.id_allocator_service.allocate("order").replace("ORD-", "MPO-"),
            "order_type": "mandiplace_order",
            "requesting_manufacturer_id": requesting_manufacturer_id,
            "supplier_manufacturer_id": "",
            "assigned_by_admin": "",
            "items": normalized_items,
            "requested_by": requested_by,
            "notes": notes,
            "qty_total": qty_total,
            "supplier_unit_price": 0.0,
            "manufacturer_unit_price": 0.0,
            "packaging": self._default_packaging(),
            "courier": self._default_courier(),
            "commission": {},
            "cost_breakdown": {},
            "status": "REQUESTED_BY_MANUFACTURER",
            "internal_status_history": [
                {"status": "REQUESTED_BY_MANUFACTURER", "at": datetime.now(UTC).isoformat(), "actor": requested_by}
            ],
            "payment_receiver": "",
            "payment_status": "PENDING",
            "payment_proof_url": "",
            "payment_proof_uploaded_at": "",
            "payment_verified_by": "",
            "payment_verified_at": "",
            "logistics": self._default_logistics(),
            "ratings": [],
        }
        created = self.governance_service.upsert_mandiplace_order(order)
        self._audit("MANDIPLACE_REQUEST_CREATED", requested_by, "manufacturer", created["mandiplace_order_id"], {"status": created.get("status", "")})
        self._emit_event(
            "MANDIPLACE_ORDER_CREATED",
            entity_type="MANDIPLACE_ORDER",
            entity_id=created["mandiplace_order_id"],
            title="MandiPlace order created",
            message=f"MandiPlace order {created['mandiplace_order_id']} was created.",
            manufacturer_code=requesting_manufacturer_id,
            manufacturer_email=requested_by,
            admin_email="PLATFORM_ADMIN",
        )
        return created

    def list_eligible_manufacturer_suppliers(self, *, mandiplace_order_id: str) -> list[dict[str, Any]]:
        if not self.governance_service:
            return []
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        requester = str(order.get("requesting_manufacturer_id") or "").strip()
        required_items = list(order.get("items", []))
        product_ids = {str(item.get("product_id") or "").strip() for item in required_items if item.get("product_id")}
        product_catalog = {
            str(item.get("product_id") or ""): item
            for item in self.governance_service.list_products()
            if item.get("status") == "ACTIVE" and item.get("available_for_mandi_network", True)
        }
        manufacturers = [item for item in self.governance_service.list_manufacturers() if item.get("status") == "ACTIVE"]
        eligible: list[dict[str, Any]] = []
        for manufacturer in manufacturers:
            supplier_code = str(manufacturer.get("manufacturer_code") or "").strip()
            if not supplier_code or supplier_code == requester:
                continue
            inventory_doc = self.dual_inventory_service.list_inventory(supplier_code)
            inventory_index = {str(item.get("product_id") or ""): item for item in inventory_doc.get("items", [])}
            supported = True
            availability_rows = []
            estimated_price = 0.0
            for request_item in required_items:
                product_id = str(request_item.get("product_id") or "").strip()
                inv = inventory_index.get(product_id, {})
                mandi_inventory = dict(inv.get("mandi_inventory") or {})
                visible = bool(mandi_inventory.get("visible_to_mandi", True))
                available_qty = int(mandi_inventory.get("available_qty", 0) or 0) - int(mandi_inventory.get("reserved_qty", 0) or 0)
                required_qty = int(float(request_item.get("qty", 0) or 0))
                owner_matches = str(product_catalog.get(product_id, {}).get("created_by_manufacturer_id") or product_catalog.get(product_id, {}).get("created_by") or "").strip()
                price = float(product_catalog.get(product_id, {}).get("approved_mandi_price", product_catalog.get(product_id, {}).get("mandi_price", 0)) or 0)
                availability_rows.append(
                    {
                        "product_id": product_id,
                        "product_name": request_item.get("name", product_id),
                        "available_qty": available_qty,
                        "required_qty": required_qty,
                        "visible_to_mandi": visible,
                        "estimated_price": price,
                    }
                )
                estimated_price += price
                if product_id not in product_ids or owner_matches != supplier_code or not visible or available_qty < required_qty:
                    supported = False
            if supported and availability_rows:
                eligible.append(
                    {
                        "manufacturer_code": supplier_code,
                        "business_name": manufacturer.get("business_name", supplier_code),
                        "city": manufacturer.get("city", ""),
                        "estimated_price": round(estimated_price / max(len(availability_rows), 1), 2),
                        "availability": availability_rows,
                    }
                )
        return eligible

    def assign_manufacturer_supplier(self, *, mandiplace_order_id: str, supplier_manufacturer_id: str, admin_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for MandiPlace requests.")
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        requester = str(order.get("requesting_manufacturer_id") or "").strip()
        supplier_code = str(supplier_manufacturer_id or "").strip().upper()
        if supplier_code == requester:
            raise ValueError("Supplier manufacturer cannot be the same as the requesting manufacturer.")
        eligible = self.list_eligible_manufacturer_suppliers(mandiplace_order_id=mandiplace_order_id)
        if supplier_code not in {item.get("manufacturer_code") for item in eligible}:
            raise ValueError("Selected supplier manufacturer is not eligible for this order.")
        order["supplier_manufacturer_id"] = supplier_code
        order["assigned_by_admin"] = admin_email
        order["status"] = "SUPPLIER_ASSIGNED"
        order.setdefault("internal_status_history", []).append({"status": "ADMIN_REVIEWING", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        order["internal_status_history"].append({"status": "SUPPLIER_ASSIGNED", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        supplier = self.governance_service.get_manufacturer(supplier_code) or {}
        self._emit_event(
            "SUPPLIER_ASSIGNED",
            entity_type="MANDIPLACE_ORDER",
            entity_id=mandiplace_order_id,
            title="MandiPlace supplier assigned",
            message=f"Supplier manufacturer assigned for {mandiplace_order_id}.",
            manufacturer_code=supplier_code,
            manufacturer_email=str(supplier.get("owner_email", "")).strip().lower(),
            admin_email=admin_email,
        )
        return updated

    def supplier_quote_mandiplace_order(
        self,
        *,
        mandiplace_order_id: str,
        supplier_manufacturer_id: str,
        supplier_unit_price: float,
        actor_email: str,
        notes: str = "",
    ) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        supplier_code = str(supplier_manufacturer_id or "").strip().upper()
        if order.get("supplier_manufacturer_id") != supplier_code:
            raise PermissionError("Manufacturer cannot quote another supplier's MandiPlace order.")
        order["supplier_unit_price"] = round(float(supplier_unit_price or 0), 2)
        order["supplier_quote_note"] = notes
        order["status"] = "SUPPLIER_QUOTED"
        order.setdefault("internal_status_history", []).append({"status": "SUPPLIER_QUOTED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        self._emit_event(
            "SUPPLIER_QUOTED",
            entity_type="MANDIPLACE_ORDER",
            entity_id=mandiplace_order_id,
            title="Supplier quoted MandiPlace order",
            message=f"Supplier quote submitted for {mandiplace_order_id}.",
            manufacturer_code=order.get("requesting_manufacturer_id", ""),
            admin_email=actor_email,
        )
        return updated

    def set_mandiplace_manufacturer_price(self, *, mandiplace_order_id: str, manufacturer_unit_price: float, admin_email: str) -> dict[str, Any]:
        if not self.pricing_service:
            raise ValueError("Pricing service not configured.")
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        order["manufacturer_unit_price"] = round(float(manufacturer_unit_price or 0), 2)
        breakdown = self.pricing_service.calculate_mandiplace_breakdown(
            qty=float(order.get("qty_total", 0) or 0),
            supplier_unit_price=float(order.get("supplier_unit_price", 0) or 0),
            manufacturer_unit_price=float(order.get("manufacturer_unit_price", 0) or 0),
            packaging_cost=float((order.get("packaging") or {}).get("total_packaging_cost", 0) or 0),
            courier_cost=float((order.get("courier") or {}).get("courier_cost", 0) or 0),
        )
        order["cost_breakdown"] = breakdown
        order["commission"] = {
            "admin_commission": breakdown.get("admin_commission", 0),
            "spread": breakdown.get("spread", 0),
            "commission_status": "CALCULATED",
        }
        order["status"] = "ADMIN_PRICE_SET"
        order.setdefault("internal_status_history", []).append({"status": "ADMIN_PRICE_SET", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        requester = self.governance_service.get_manufacturer(updated.get("requesting_manufacturer_id", "")) or {}
        self._emit_event(
            "ADMIN_PRICE_SET",
            entity_type="MANDIPLACE_ORDER",
            entity_id=mandiplace_order_id,
            title="MandiPlace price set",
            message=f"Admin price was set for {mandiplace_order_id}.",
            manufacturer_code=updated.get("requesting_manufacturer_id", ""),
            manufacturer_email=str(requester.get("owner_email", "")).strip().lower(),
            admin_email=admin_email,
        )
        return updated

    def apply_packaging_to_mandiplace_order(
        self,
        *,
        mandiplace_order_id: str,
        packaging_service_id: str,
        qty: float,
        actor_email: str,
        packaging_note: str = "",
    ) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        service = self.governance_service.get_packaging_service(packaging_service_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        if not service or service.get("status") != "ACTIVE":
            raise ValueError("Packaging service is not available.")
        qty_value = float(qty or 0)
        total_cost = max(round(float(service.get("base_price", 0) or 0) + qty_value * float(service.get("price_per_unit", 0) or 0), 2), float(service.get("minimum_charge", 0) or 0))
        order["packaging"] = {
            "packaging_service_id": service.get("packaging_service_id", ""),
            "packaging_name": service.get("name", ""),
            "qty": qty_value,
            "unit_price": float(service.get("price_per_unit", 0) or 0),
            "total_packaging_cost": total_cost,
            "packaging_note": packaging_note,
        }
        order["status"] = "PACKAGING_SELECTED"
        order["cost_breakdown"] = self.pricing_service.calculate_mandiplace_breakdown(
            qty=float(order.get("qty_total", 0) or 0),
            supplier_unit_price=float(order.get("supplier_unit_price", 0) or 0),
            manufacturer_unit_price=float(order.get("manufacturer_unit_price", 0) or 0),
            packaging_cost=total_cost,
            courier_cost=float((order.get("courier") or {}).get("courier_cost", 0) or 0),
        )
        order.setdefault("internal_status_history", []).append({"status": "PACKAGING_SELECTED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        self._emit_event(
            "PACKAGING_SELECTED",
            entity_type="MANDIPLACE_ORDER",
            entity_id=mandiplace_order_id,
            title="Packaging selected",
            message=f"Packaging selected for {mandiplace_order_id}.",
            manufacturer_code=updated.get("requesting_manufacturer_id", ""),
            admin_email=actor_email,
        )
        return updated

    def book_courier_for_mandiplace_order(
        self,
        *,
        mandiplace_order_id: str,
        courier_service_id: str,
        pickup_location: str,
        delivery_location: str,
        distance_km: float,
        weight_kg: float,
        actor_email: str,
        tracking_reference: str = "",
        driver_name: str = "",
        driver_mobile: str = "",
        vehicle_number: str = "",
    ) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        service = self.governance_service.get_courier_service(courier_service_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        if not service or service.get("status") != "ACTIVE":
            raise ValueError("Courier service is not available.")
        courier_cost = max(
            round(
                float(service.get("base_price", 0) or 0)
                + float(distance_km or 0) * float(service.get("price_per_km", 0) or 0)
                + float(weight_kg or 0) * float(service.get("price_per_kg", 0) or 0),
                2,
            ),
            float(service.get("minimum_charge", 0) or 0),
        )
        order["courier"] = {
            "courier_service_id": service.get("courier_service_id", ""),
            "provider_name": service.get("provider_name", ""),
            "pickup_location": pickup_location,
            "delivery_location": delivery_location,
            "distance_km": float(distance_km or 0),
            "weight_kg": float(weight_kg or 0),
            "courier_cost": courier_cost,
            "tracking_reference": tracking_reference,
            "driver_name": driver_name,
            "driver_mobile": driver_mobile,
            "vehicle_number": vehicle_number,
            "status": "BOOKED",
        }
        order.setdefault("logistics", self._default_logistics())
        order["logistics"].update(
            {
                "transport_mode": service.get("service_type", ""),
                "driver_name": driver_name,
                "driver_mobile": driver_mobile,
                "vehicle_number": vehicle_number,
                "expected_delivery": "",
                "delivery_status": "BOOKED",
            }
        )
        order["status"] = "COURIER_BOOKED"
        order["cost_breakdown"] = self.pricing_service.calculate_mandiplace_breakdown(
            qty=float(order.get("qty_total", 0) or 0),
            supplier_unit_price=float(order.get("supplier_unit_price", 0) or 0),
            manufacturer_unit_price=float(order.get("manufacturer_unit_price", 0) or 0),
            packaging_cost=float((order.get("packaging") or {}).get("total_packaging_cost", 0) or 0),
            courier_cost=courier_cost,
        )
        order.setdefault("internal_status_history", []).append({"status": "COURIER_BOOKED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        self._emit_event(
            "COURIER_BOOKED",
            entity_type="MANDIPLACE_ORDER",
            entity_id=mandiplace_order_id,
            title="Courier booked",
            message=f"Courier booked for {mandiplace_order_id}.",
            manufacturer_code=updated.get("requesting_manufacturer_id", ""),
            admin_email=actor_email,
        )
        return updated

    def confirm_mandiplace_order(self, *, mandiplace_order_id: str, manufacturer_code: str, actor_email: str) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        if order.get("requesting_manufacturer_id") != manufacturer_code:
            raise PermissionError("Manufacturer cannot confirm another manufacturer's MandiPlace order.")
        breakdown = dict(order.get("cost_breakdown") or {})
        if not breakdown:
            breakdown = self.pricing_service.calculate_mandiplace_breakdown(
                qty=float(order.get("qty_total", 0) or 0),
                supplier_unit_price=float(order.get("supplier_unit_price", 0) or 0),
                manufacturer_unit_price=float(order.get("manufacturer_unit_price", 0) or 0),
                packaging_cost=float((order.get("packaging") or {}).get("total_packaging_cost", 0) or 0),
                courier_cost=float((order.get("courier") or {}).get("courier_cost", 0) or 0),
            )
        order["cost_breakdown"] = breakdown
        order["commission"] = {
            "admin_commission": breakdown.get("admin_commission", 0),
            "spread": breakdown.get("spread", 0),
            "commission_status": "DUE",
        }
        inventory_items = [
            {"product_id": item.get("product_id", ""), "qty": int(float(item.get("qty", 0) or 0))}
            for item in order.get("items", [])
            if item.get("product_id")
        ]
        if inventory_items:
            self.dual_inventory_service.reserve_mandi_inventory(
                str(order.get("supplier_manufacturer_id", "")).strip().upper(),
                inventory_items,
                related_order_id=mandiplace_order_id,
                note="MandiPlace order reserved after manufacturer confirmation",
                created_by=actor_email,
            )
        order["payment_receiver"] = order.get("supplier_manufacturer_id", "")
        order["status"] = "MANUFACTURER_CONFIRMED"
        order.setdefault("internal_status_history", []).append({"status": "MANUFACTURER_CONFIRMED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        self.ledger_service.create_entry(
            manufacturer_code,
            party_a=manufacturer_code,
            party_b=order.get("supplier_manufacturer_id", "") or "ADMIN_ROUTED_SUPPLIER",
            entry_type="MANDIPLACE_LEDGER",
            amount=float(breakdown.get("goods_amount", 0) or 0),
            paid_amount=0,
            ledger_days=7,
            note=f"Admin-routed MandiPlace order {mandiplace_order_id}",
            metadata={
                "ledger_scope": "mandiplace_ledger",
                "mandiplace_order_id": mandiplace_order_id,
                "payment_receiver": order.get("supplier_manufacturer_id", ""),
                "cost_breakdown": breakdown,
            },
        )
        self.ledger_service.create_entry(
            manufacturer_code,
            party_a=manufacturer_code,
            party_b="PLATFORM_ADMIN",
            entry_type="MANDIPLACE_COMMISSION",
            amount=float(breakdown.get("admin_commission", 0) or 0),
            paid_amount=0,
            ledger_days=7,
            note=f"Commission due for MandiPlace order {mandiplace_order_id}",
            metadata={
                "ledger_scope": "mandiplace_commission",
                "mandiplace_order_id": mandiplace_order_id,
            },
        )
        if float(breakdown.get("packaging_cost", 0) or 0) > 0 or float(breakdown.get("courier_cost", 0) or 0) > 0:
            self.ledger_service.create_entry(
                manufacturer_code,
                party_a=manufacturer_code,
                party_b="PLATFORM_ADMIN",
                entry_type="MANDIPLACE_SERVICE",
                amount=float(breakdown.get("packaging_cost", 0) or 0) + float(breakdown.get("courier_cost", 0) or 0),
                paid_amount=0,
                ledger_days=7,
                note=f"Packaging/courier due for MandiPlace order {mandiplace_order_id}",
                metadata={
                    "ledger_scope": "mandiplace_service",
                    "mandiplace_order_id": mandiplace_order_id,
                },
            )
        updated = self.governance_service.upsert_mandiplace_order(order)
        if self.settlement_service:
            self.settlement_service.ensure_transaction(
                transaction_type="MANDIPLACE",
                related_order_id=mandiplace_order_id,
                payer_role="manufacturer",
                payer_id=manufacturer_code,
                payee_role="manufacturer",
                payee_id=order.get("supplier_manufacturer_id", "") or "ADMIN_ROUTED_SUPPLIER",
                gross_amount=float(breakdown.get("goods_amount", 0) or 0),
                commission_amount=float(breakdown.get("admin_commission", 0) or 0),
                packaging_amount=float(breakdown.get("packaging_cost", 0) or 0),
                courier_amount=float(breakdown.get("courier_cost", 0) or 0),
                net_amount=float(breakdown.get("final_payable", 0) or 0),
                status="PENDING",
                due_date=(datetime.now(UTC).date()).isoformat(),
                created_by=actor_email,
                metadata={"mandiplace_order_id": mandiplace_order_id, "cost_breakdown": breakdown},
            )
            if self.invoice_service:
                self.invoice_service.generate_invoice(
                    invoice_type="MANDI_INVOICE",
                    related_order_id=mandiplace_order_id,
                    bill_from={"manufacturer_code": order.get("supplier_manufacturer_id", ""), "name": order.get("supplier_manufacturer_id", "")},
                    bill_to={"manufacturer_code": manufacturer_code, "name": manufacturer_code},
                    items=[
                        {
                            "name": item.get("name", ""),
                            "qty": item.get("qty", 0),
                            "unit": item.get("unit", ""),
                            "unit_price": order.get("manufacturer_unit_price", 0),
                        }
                        for item in order.get("items", [])
                    ],
                    subtotal=float(breakdown.get("goods_amount", 0) or 0),
                    packaging_amount=float(breakdown.get("packaging_cost", 0) or 0),
                    courier_amount=float(breakdown.get("courier_cost", 0) or 0),
                    commission_amount=float(breakdown.get("admin_commission", 0) or 0),
                )
        return updated

    def dispatch_mandiplace_order(self, *, mandiplace_order_id: str, supplier_manufacturer_id: str, actor_email: str) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        supplier_code = str(supplier_manufacturer_id or "").strip().upper()
        if order.get("supplier_manufacturer_id") != supplier_code:
            raise PermissionError("Manufacturer cannot dispatch another supplier's MandiPlace order.")
        inventory_items = [
            {"product_id": item.get("product_id", ""), "qty": int(float(item.get("qty", 0) or 0))}
            for item in order.get("items", [])
            if item.get("product_id")
        ]
        inventory_service = self._inventory_service()
        if inventory_items and inventory_service:
            for item in inventory_items:
                record = inventory_service.get_inventory_by_keys(
                    owner_role="manufacturer",
                    owner_id=supplier_code,
                    item_type="PRODUCT",
                    item_id=str(item.get("product_id", "")),
                    network="MANDIPLACE",
                )
                if record:
                    inventory_service.mark_dispatched(
                        inventory_id=record["inventory_id"],
                        qty=int(float(item.get("qty", 0) or 0)),
                        related_order_id=mandiplace_order_id,
                        note="MandiPlace order dispatched",
                        created_by=actor_email,
                    )
        order["status"] = "SUPPLIER_DISPATCHED"
        order.setdefault("courier", self._default_courier())
        if order["courier"]:
            order["courier"]["status"] = "IN_TRANSIT"
        order.setdefault("logistics", self._default_logistics())
        order["logistics"]["dispatch_time"] = datetime.now(UTC).isoformat()
        order["logistics"]["delivery_status"] = "IN_TRANSIT"
        order.setdefault("internal_status_history", []).append({"status": "SUPPLIER_DISPATCHED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        order["internal_status_history"].append({"status": "IN_TRANSIT", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        requester = self.governance_service.get_manufacturer(updated.get("requesting_manufacturer_id", "")) or {}
        self._emit_event(
            "ORDER_DISPATCHED",
            entity_type="MANDIPLACE_ORDER",
            entity_id=mandiplace_order_id,
            title="MandiPlace order dispatched",
            message=f"MandiPlace order {mandiplace_order_id} was dispatched.",
            manufacturer_code=updated.get("requesting_manufacturer_id", ""),
            manufacturer_email=str(requester.get("owner_email", "")).strip().lower(),
            admin_email=actor_email,
        )
        return updated

    def update_mandiplace_courier_status(self, *, mandiplace_order_id: str, actor_email: str, status: str) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        normalized = str(status or "").strip().upper()
        order.setdefault("courier", self._default_courier())
        order["courier"]["status"] = normalized
        order.setdefault("logistics", self._default_logistics())
        order["logistics"]["delivery_status"] = normalized
        if normalized == "DELIVERED":
            order["status"] = "DELIVERED"
            order["logistics"]["delivered_at"] = datetime.now(UTC).isoformat()
            order.setdefault("internal_status_history", []).append({"status": "DELIVERED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
            self._emit_event(
                "ORDER_DELIVERED",
                entity_type="MANDIPLACE_ORDER",
                entity_id=mandiplace_order_id,
                title="MandiPlace order delivered",
                message=f"MandiPlace order {mandiplace_order_id} reached delivery stage.",
                manufacturer_code=order.get("requesting_manufacturer_id", ""),
                admin_email=actor_email,
            )
        else:
            order.setdefault("internal_status_history", []).append({"status": normalized, "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        return self.governance_service.upsert_mandiplace_order(order)

    def receive_mandiplace_order(self, *, mandiplace_order_id: str, manufacturer_code: str, actor_email: str) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        if order.get("requesting_manufacturer_id") != manufacturer_code:
            raise PermissionError("Manufacturer cannot receive another manufacturer's MandiPlace order.")
        inventory_items = [
            {"product_id": item.get("product_id", ""), "qty": int(float(item.get("qty", 0) or 0))}
            for item in order.get("items", [])
            if item.get("product_id")
        ]
        if inventory_items:
            self.dual_inventory_service.finalize_reserved(
                str(order.get("supplier_manufacturer_id", "")).strip().upper(),
                inventory_items,
                bucket="mandi_inventory",
                related_order_id=mandiplace_order_id,
                note="MandiPlace order received",
                created_by=actor_email,
            )
            inventory_service = self._inventory_service()
            if inventory_service:
                for item in inventory_items:
                    record = inventory_service.get_inventory_by_keys(
                        owner_role="manufacturer",
                        owner_id=str(order.get("supplier_manufacturer_id", "")).strip().upper(),
                        item_type="PRODUCT",
                        item_id=str(item.get("product_id", "")),
                        network="MANDIPLACE",
                    )
                    if record:
                        inventory_service.mark_received(
                            inventory_id=record["inventory_id"],
                            qty=int(float(item.get("qty", 0) or 0)),
                            related_order_id=mandiplace_order_id,
                            note="MandiPlace order received",
                            created_by=actor_email,
                        )
        order["status"] = "RECEIVED"
        order.setdefault("logistics", self._default_logistics())
        order["logistics"]["delivery_status"] = "DELIVERED"
        order["logistics"]["delivered_at"] = datetime.now(UTC).isoformat()
        order.setdefault("internal_status_history", []).append({"status": "RECEIVED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_mandiplace_order(order)
        return updated

    def close_mandiplace_order(self, *, mandiplace_order_id: str, admin_email: str) -> dict[str, Any]:
        order = self.governance_service.get_mandiplace_order(mandiplace_order_id)
        if not order:
            raise ValueError("MandiPlace order not found.")
        if order.get("status") != "RECEIVED":
            raise ValueError("Only received MandiPlace orders can be closed.")
        order["status"] = "CLOSED"
        order.setdefault("internal_status_history", []).append({"status": "CLOSED", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        return self.governance_service.upsert_mandiplace_order(order)

    def create_supply_request(
        self,
        *,
        manufacturer_code: str,
        raw_material_id: str,
        qty: float,
        unit: str,
        requested_by: str,
        notes: str = "",
    ) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = {
            "mandi_order_id": self.id_allocator_service.allocate("order").replace("ORD-", "MO-"),
            "order_type": "mandi_order",
            "raw_material_id": raw_material_id,
            "manufacturer_id": manufacturer_code,
            "mahajan_id": "",
            "supplier_type": "",
            "route_type": "ADMIN_ROUTED",
            "qty": float(qty or 0),
            "unit": unit,
            "requested_by": requested_by,
            "notes": notes,
            "status": "REQUESTED_BY_MANUFACTURER",
            "payment_receiver": "",
            "payment_proof_url": "",
            "payment_proof_uploaded_at": "",
            "payment_verified_by": "",
            "payment_verified_at": "",
            "logistics": self._default_logistics(),
            "internal_status_history": [
                {"status": "REQUESTED_BY_MANUFACTURER", "at": datetime.now(UTC).isoformat(), "actor": requested_by}
            ],
            "ratings": [],
        }
        created = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_REQUEST_CREATED", requested_by, "manufacturer", created["mandi_order_id"], {"status": created.get("status", ""), "raw_material_id": raw_material_id})
        self._emit_event(
            "MANDI_ORDER_CREATED",
            entity_type="MANDI_ORDER",
            entity_id=created["mandi_order_id"],
            title="Mandi order created",
            message=f"Mandi order {created['mandi_order_id']} was created.",
            manufacturer_code=manufacturer_code,
            manufacturer_email=requested_by,
        )
        return created

    def assign_supply_to_mahajan(self, *, mandi_order_id: str, mahajan_id: str, admin_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        order["mahajan_id"] = mahajan_id
        order["supplier_type"] = "MAHAJAN"
        order["status"] = "SENT_TO_MAHAJAN"
        order.setdefault("internal_status_history", []).append({"status": "ADMIN_REVIEWING", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        order["internal_status_history"].append({"status": "SENT_TO_MAHAJAN", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_ASSIGNED", admin_email, "platform_admin", mandi_order_id, {"mahajan_id": mahajan_id, "status": updated.get("status", "")})
        self._emit_event(
            "SUPPLY_ORDER_ASSIGNED",
            entity_type="SUPPLY_ORDER",
            entity_id=mandi_order_id,
            title="Supply order assigned",
            message=f"Supply order {mandi_order_id} was assigned to mahajan.",
            manufacturer_code=updated.get("manufacturer_id", ""),
            mahajan_id=mahajan_id,
            admin_email=admin_email,
        )
        return updated

    def quote_supply_order(self, *, mandi_order_id: str, mahajan_id: str, mahajan_unit_price: float, mahajan_email: str, notes: str = "") -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("mahajan_id") and order.get("mahajan_id") != mahajan_id:
            raise PermissionError("Mahajan cannot quote another mahajan's supply order.")
        order["mahajan_id"] = mahajan_id
        order["supplier_type"] = "MAHAJAN"
        order["mahajan_unit_price"] = round(float(mahajan_unit_price or 0), 2)
        order["mahajan_notes"] = notes
        order["status"] = "MAHAJAN_QUOTED"
        order["payment_receiver"] = mahajan_id
        order.setdefault("internal_status_history", []).append({"status": "MAHAJAN_QUOTED", "at": datetime.now(UTC).isoformat(), "actor": mahajan_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_QUOTED", mahajan_email, "mahajan", mandi_order_id, {"mahajan_id": mahajan_id, "mahajan_unit_price": order.get("mahajan_unit_price", 0), "status": updated.get("status", "")})
        return updated

    def set_manufacturer_supply_price(
        self,
        *,
        mandi_order_id: str,
        manufacturer_unit_price: float,
        admin_email: str,
        mahajan_fee_percent: float | None = None,
    ) -> dict[str, Any]:
        if not self.governance_service or not self.pricing_service:
            raise ValueError("Supply pricing services are not configured.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        commission = self.pricing_service.calculate_supply_commission(
            mandi_order_id=mandi_order_id,
            mahajan_id=order.get("mahajan_id", ""),
            manufacturer_id=order.get("manufacturer_id", ""),
            raw_material_id=order.get("raw_material_id", ""),
            qty=float(order.get("qty", 0) or 0),
            unit=str(order.get("unit", "")),
            mahajan_unit_price=float(order.get("mahajan_unit_price", 0) or 0),
            manufacturer_unit_price=float(manufacturer_unit_price or 0),
            mahajan_fee_percent=mahajan_fee_percent,
        )
        order["manufacturer_unit_price"] = round(float(manufacturer_unit_price or 0), 2)
        order["commission_object"] = commission
        order["status"] = "ADMIN_PRICE_SET"
        order.setdefault("internal_status_history", []).append({"status": "ADMIN_PRICE_SET", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_PRICE_SET", admin_email, "platform_admin", mandi_order_id, {"manufacturer_unit_price": order.get("manufacturer_unit_price", 0), "status": updated.get("status", "")})
        return updated

    def confirm_supply_order(self, *, mandi_order_id: str, manufacturer_code: str, actor_email: str) -> dict[str, Any]:
        if not self.governance_service or not self.pricing_service:
            raise ValueError("Supply pricing services are not configured.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("manufacturer_id") != manufacturer_code:
            raise PermissionError("Manufacturer cannot confirm another manufacturer's supply order.")
        self._reserve_supply_inventory(order, actor_email=actor_email)
        order["status"] = "MANUFACTURER_CONFIRMED"
        order.setdefault("internal_status_history", []).append({"status": "MANUFACTURER_CONFIRMED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        commission = dict(order.get("commission_object") or {})
        if not commission:
            commission = self.pricing_service.calculate_supply_commission(
                mandi_order_id=mandi_order_id,
                mahajan_id=order.get("mahajan_id", ""),
                manufacturer_id=order.get("manufacturer_id", ""),
                raw_material_id=order.get("raw_material_id", ""),
                qty=float(order.get("qty", 0) or 0),
                unit=str(order.get("unit", "")),
                mahajan_unit_price=float(order.get("mahajan_unit_price", 0) or 0),
                manufacturer_unit_price=float(order.get("manufacturer_unit_price", 0) or 0),
            )
            order["commission_object"] = commission
        self.ledger_service.create_entry(
            manufacturer_code,
            party_a=manufacturer_code,
            party_b=order.get("mahajan_id", "") or "ADMIN_ROUTED_SUPPLIER",
            entry_type="MANDI_LEDGER",
            amount=float(commission.get("manufacturer_bill_amount", 0) or 0),
            paid_amount=0,
            ledger_days=7,
            note=f"Admin-managed mandi supply order {mandi_order_id}",
            metadata={
                "ledger_scope": "mandi_ledger",
                "supply_order": mandi_order_id,
                "order_id": mandi_order_id,
                "commission_object": commission,
                "payment_receiver": order.get("mahajan_id", "") or "SUPPLIER_DIRECT",
                "routed_by": "platform_admin",
            },
        )
        self.governance_service.create_supply_ledger_entry(
            {
                "entry_id": self.id_allocator_service.allocate("ledger_entry"),
                "mandi_order_id": mandi_order_id,
                "mahajan_id": order.get("mahajan_id", ""),
                "manufacturer_id": manufacturer_code,
                "entry_type": "SUPPLY_LEDGER",
                "amount_due_to_mahajan": round(float(commission.get("mahajan_bill_amount", 0) or 0) - float(commission.get("mahajan_transaction_fee", 0) or 0), 2),
                "mahajan_transaction_fee": float(commission.get("mahajan_transaction_fee", 0) or 0),
                "status": "PENDING",
                "payment_receiver": order.get("mahajan_id", ""),
                "commission_status": "DUE",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        updated = self.governance_service.upsert_supply_order(order)
        if self.settlement_service:
            self.settlement_service.ensure_transaction(
                transaction_type="SUPPLY",
                related_order_id=mandi_order_id,
                payer_role="manufacturer",
                payer_id=manufacturer_code,
                payee_role="mahajan",
                payee_id=order.get("mahajan_id", "") or "ADMIN_ROUTED_SUPPLIER",
                gross_amount=float(commission.get("manufacturer_bill_amount", 0) or 0),
                commission_amount=float(commission.get("admin_total_earning", 0) or 0),
                net_amount=float(commission.get("manufacturer_bill_amount", 0) or 0),
                status="PENDING",
                due_date=(datetime.now(UTC).date()).isoformat(),
                created_by=actor_email,
                metadata={"mandi_order_id": mandi_order_id, "commission_object": commission},
            )
            if self.invoice_service:
                material = self.governance_service.get_supply_order(mandi_order_id) or {}
                self.invoice_service.generate_invoice(
                    invoice_type="SUPPLY_INVOICE",
                    related_order_id=mandi_order_id,
                    bill_from={"mahajan_id": order.get("mahajan_id", ""), "name": order.get("mahajan_id", "")},
                    bill_to={"manufacturer_code": manufacturer_code, "name": manufacturer_code},
                    items=[
                        {
                            "name": material.get("raw_material_id", ""),
                            "qty": material.get("qty", 0),
                            "unit": material.get("unit", ""),
                            "unit_price": commission.get("manufacturer_unit_price", 0),
                        }
                    ],
                    subtotal=float(commission.get("manufacturer_bill_amount", 0) or 0),
                    commission_amount=float(commission.get("admin_total_earning", 0) or 0),
                )
        self._audit("SUPPLY_CONFIRMED", actor_email, "manufacturer", mandi_order_id, {"status": updated.get("status", "")})
        self._emit_event(
            "SUPPLY_ORDER_CONFIRMED",
            entity_type="SUPPLY_ORDER",
            entity_id=mandi_order_id,
            title="Supply order confirmed",
            message=f"Supply order {mandi_order_id} was confirmed.",
            manufacturer_code=manufacturer_code,
            manufacturer_email=actor_email,
            mahajan_id=updated.get("mahajan_id", ""),
        )
        return updated

    def dispatch_supply_order(self, *, mandi_order_id: str, mahajan_id: str, actor_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("mahajan_id") != mahajan_id:
            raise PermissionError("Mahajan cannot dispatch another mahajan's order.")
        self._mark_supply_inventory_dispatched(order, actor_email=actor_email)
        order["status"] = "MAHAJAN_DISPATCHED"
        order.setdefault("logistics", self._default_logistics())
        order["logistics"]["delivery_status"] = "DISPATCHED"
        order["logistics"]["dispatch_time"] = datetime.now(UTC).isoformat()
        order.setdefault("internal_status_history", []).append({"status": "MAHAJAN_DISPATCHED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_DISPATCHED", actor_email, "mahajan", mandi_order_id, {"status": updated.get("status", ""), "delivery_status": updated.get("logistics", {}).get("delivery_status", "")})
        return updated

    def receive_supply_order(self, *, mandi_order_id: str, manufacturer_code: str, actor_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("manufacturer_id") != manufacturer_code:
            raise PermissionError("Manufacturer cannot receive another manufacturer's supply order.")
        self._complete_supply_inventory(order, actor_email=actor_email)
        order["status"] = "MANUFACTURER_RECEIVED"
        order.setdefault("logistics", self._default_logistics())
        order["logistics"]["delivery_status"] = "DELIVERED"
        order["logistics"]["delivered_at"] = datetime.now(UTC).isoformat()
        order.setdefault("internal_status_history", []).append({"status": "MANUFACTURER_RECEIVED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_RECEIVED", actor_email, "manufacturer", mandi_order_id, {"status": updated.get("status", ""), "delivery_status": updated.get("logistics", {}).get("delivery_status", "")})
        return updated

    def close_supply_order(self, *, mandi_order_id: str, admin_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("status") != "MANUFACTURER_RECEIVED":
            raise ValueError("Only received mandi orders can be closed.")
        order["status"] = "CLOSED"
        order.setdefault("internal_status_history", []).append({"status": "CLOSED", "at": datetime.now(UTC).isoformat(), "actor": admin_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_CLOSED", admin_email, "platform_admin", mandi_order_id, {"status": updated.get("status", "")})
        return updated

    def cancel_supply_order(self, *, mandi_order_id: str, admin_email: str, reason: str = "") -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        if order.get("status") in {"MANUFACTURER_RECEIVED", "CLOSED"}:
            raise ValueError("Received or closed mandi orders cannot be cancelled.")
        if order.get("status") == "MANUFACTURER_CONFIRMED":
            self._release_supply_inventory(order, actor_email=admin_email, note="Supply order cancelled")
        order["status"] = "CANCELLED"
        if reason:
            order["cancellation_reason"] = reason
        order.setdefault("internal_status_history", []).append({"status": "CANCELLED", "at": datetime.now(UTC).isoformat(), "actor": admin_email, "reason": reason})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_CANCELLED", admin_email, "platform_admin", mandi_order_id, {"status": updated.get("status", ""), "reason": reason})
        return updated

    def update_supply_logistics(
        self,
        *,
        mandi_order_id: str,
        actor_email: str,
        transport_mode: str = "",
        driver_name: str = "",
        driver_mobile: str = "",
        vehicle_number: str = "",
        dispatch_note: str = "",
        proof_url: str = "",
        delivery_status: str = "",
        expected_delivery: str = "",
    ) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        logistics = dict(order.get("logistics") or self._default_logistics())
        logistics.update(
            {
                "logistics_owner": "platform_admin",
                "transport_mode": transport_mode or logistics.get("transport_mode", ""),
                "driver_name": driver_name or logistics.get("driver_name", ""),
                "driver_mobile": driver_mobile or logistics.get("driver_mobile", ""),
                "vehicle_number": vehicle_number or logistics.get("vehicle_number", ""),
                "dispatch_time": datetime.now(UTC).isoformat() if delivery_status.upper() == "DISPATCHED" and not logistics.get("dispatch_time") else logistics.get("dispatch_time", ""),
                "expected_delivery": expected_delivery or logistics.get("expected_delivery", ""),
                "dispatch_note": dispatch_note or logistics.get("dispatch_note", ""),
                "delivery_note": dispatch_note or logistics.get("delivery_note", ""),
                "proof_url": proof_url or logistics.get("proof_url", ""),
                "proof_image_url": proof_url or logistics.get("proof_image_url", ""),
                "delivery_status": delivery_status or logistics.get("delivery_status", ""),
            }
        )
        order["logistics"] = logistics
        order.setdefault("internal_status_history", []).append({"status": "LOGISTICS_UPDATED", "at": datetime.now(UTC).isoformat(), "actor": actor_email})
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_LOGISTICS_UPDATED", actor_email, "platform_admin", mandi_order_id, {"delivery_status": updated.get("logistics", {}).get("delivery_status", ""), "vehicle_number": updated.get("logistics", {}).get("vehicle_number", "")})
        self._emit_event(
            "LOGISTICS_UPDATED",
            entity_type="SUPPLY_ORDER",
            entity_id=mandi_order_id,
            title="Supply logistics updated",
            message=f"Logistics updated for supply order {mandi_order_id}.",
            manufacturer_code=updated.get("manufacturer_id", ""),
            mahajan_id=updated.get("mahajan_id", ""),
        )
        return updated

    def attach_payment_proof(self, *, mandi_order_id: str, actor_email: str, proof_url: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        order["payment_proof_url"] = proof_url.strip()
        order["payment_proof_uploaded_at"] = datetime.now(UTC).isoformat()
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_PAYMENT_PROOF_ATTACHED", actor_email, "system", mandi_order_id, {"payment_proof_url": updated.get("payment_proof_url", "")})
        return updated

    def verify_payment_proof(self, *, mandi_order_id: str, verifier_email: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        order["payment_verified_by"] = verifier_email
        order["payment_verified_at"] = datetime.now(UTC).isoformat()
        updated = self.governance_service.upsert_supply_order(order)
        if self.settlement_service:
            transaction = next(
                (item for item in self.settlement_service.list_transactions() if item.get("related_order_id") == mandi_order_id and item.get("transaction_type") == "SUPPLY"),
                None,
            )
            if transaction:
                self.settlement_service.record_payment(
                    financial_transaction_id=transaction["financial_transaction_id"],
                    amount=float(transaction.get("gross_amount", 0) or 0),
                    actor_id=verifier_email,
                    payment_reference=str(order.get("payment_reference", "")),
                    payment_proof_url=str(order.get("payment_proof_url", "")),
                    verified=True,
                    note="Supply payment proof verified",
                )
        self._audit("SUPPLY_PAYMENT_PROOF_VERIFIED", verifier_email, "platform_admin", mandi_order_id, {"payment_verified_at": updated.get("payment_verified_at", "")})
        self._emit_event(
            "PAYMENT_VERIFIED",
            entity_type="SUPPLY_ORDER",
            entity_id=mandi_order_id,
            title="Supply payment verified",
            message=f"Payment was verified for supply order {mandi_order_id}.",
            manufacturer_code=updated.get("manufacturer_id", ""),
            mahajan_id=updated.get("mahajan_id", ""),
            admin_email=verifier_email,
        )
        return updated

    def submit_feedback(self, *, mandi_order_id: str, rating: int, feedback: str, submitted_by: str) -> dict[str, Any]:
        if not self.governance_service:
            raise ValueError("Governance service not configured for supply requests.")
        order = self.governance_service.get_supply_order(mandi_order_id)
        if not order:
            raise ValueError("Supply order not found.")
        ratings = list(order.get("ratings", []))
        ratings.append(
            {
                "rating": max(1, min(int(rating or 0), 5)),
                "feedback": feedback.strip(),
                "submitted_by": submitted_by,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        order["ratings"] = ratings
        updated = self.governance_service.upsert_supply_order(order)
        self._audit("SUPPLY_FEEDBACK_SUBMITTED", submitted_by, "manufacturer", mandi_order_id, {"rating": ratings[-1]["rating"]})
        return updated

    def respond_to_rfq(self, current_user, rfq_owner_code: str, rfq_id: str, available_items: list[dict[str, Any]], supplier_terms: dict[str, Any]) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        context = ProcurementContext(transaction_id=transaction_id, state="RUNNING")
        self._write_journal(context)
        rfq_path = self.domain_paths.rfq_path(rfq_owner_code)
        inventory_path = self.domain_paths.private_self_inventory_path(current_user.manufacturer_code)
        try:
            normalized_items = self._validate_available_items(available_items)
            self._register_target(context, rfq_path)
            self._register_target(context, inventory_path)
            self.dual_inventory_service.reserve_mandi_inventory(
                current_user.manufacturer_code,
                [{"product_id": item["product_id"], "qty": item["qty"]} for item in normalized_items],
                related_order_id=rfq_id,
                note="RFQ supplier stock reserved",
                created_by=current_user.email,
            )
            response = {
                "response_id": self.id_allocator_service.allocate("response"),
                "supplier_manufacturer_id": current_user.manufacturer_code,
                "rfq_id": rfq_id,
                "available_items": normalized_items,
                "supplier_terms": supplier_terms,
                "status": "SUBMITTED",
                "created_at": datetime.now(UTC).isoformat(),
            }

            def mutator(payload: dict[str, Any]) -> dict[str, Any]:
                payload.setdefault("rfqs", [])
                payload.setdefault("responses", [])
                rfq = next((item for item in payload["rfqs"] if item.get("rfq_id") == rfq_id), None)
                if rfq is None:
                    raise ValueError(f"Sourcing request not found: {rfq_id}")
                if rfq.get("status") != "OPEN":
                    raise ValueError("Sourcing request is not open for responses.")
                rfq["status"] = "RESPONDED"
                payload["responses"].append(response)
                return payload

            self.safe_drive_write_service.mutate_json(rfq_path, mutator)
            self.notification_center_service.create_notification(
                rfq_owner_code,
                user_id=rfq_owner_code,
                notification_type="RFQ_ACCEPTED",
                priority="HIGH",
                title="Mandi Sourcing Response Received",
                message="A supplier responded to your mandi sourcing request.",
                source_type="RFQ",
                source_id=rfq_id,
            )
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return response

    def accept_rfq_response(self, buyer_user, rfq_id: str, response_id: str) -> dict[str, Any]:
        transaction_id = self.id_allocator_service.allocate("transaction")
        context = ProcurementContext(transaction_id=transaction_id, state="RUNNING")
        self._write_journal(context)
        rfq_path = self.domain_paths.rfq_path(buyer_user.manufacturer_code)
        try:
            self._register_target(context, rfq_path)
            payload = self._rfq_doc(buyer_user.manufacturer_code)
            rfq = next((item for item in payload.get("rfqs", []) if item.get("rfq_id") == rfq_id), None)
            response = next((item for item in payload.get("responses", []) if item.get("response_id") == response_id), None)
            if rfq is None or response is None:
                raise ValueError("Sourcing response not found.")
            total_amount = round(sum(float(item.get("total_price", 0) or 0) for item in response.get("available_items", [])), 2)
            if total_amount <= 0:
                raise ValueError("Buyer cannot accept a sourcing response without valid priced items.")
            rfq["status"] = "BUYER_CONFIRMED"
            response["status"] = "BUYER_CONFIRMED"
            self.safe_drive_write_service.replace_document(rfq_path, payload)
            confirmation = self.trade_confirmation_service.create_confirmation(
                buyer_user.manufacturer_code,
                source_type="MANDI_RFQ",
                source_id=rfq_id,
                confirmed_by=buyer_user.email,
                accepted_terms_snapshot={"rfq": rfq, "response": response},
            )
            rfq["trade_confirmation_id"] = confirmation["confirmation_id"]
            self.safe_drive_write_service.replace_document(rfq_path, payload)
            self.ledger_service.create_entry(
                buyer_user.manufacturer_code,
                party_a=buyer_user.manufacturer_code,
                party_b=response["supplier_manufacturer_id"],
                entry_type="MANDI_SUPPLY",
                amount=total_amount,
                paid_amount=0,
                ledger_days=int(response.get("supplier_terms", {}).get("ledger_days", 0)),
                note=response.get("supplier_terms", {}).get("freestyle_note", ""),
            )
            context.state = "COMMITTED"
            self._write_journal(context)
        except Exception as exc:  # noqa: BLE001
            context.state = "ROLLED_BACK"
            context.error_message = str(exc)
            self.rollback_service.restore_files(context.backup_targets)
            self._write_journal(context)
            raise
        return {"rfq_id": rfq_id, "response_id": response_id, "status": "BUYER_CONFIRMED"}

    def recover_incomplete_transactions(self) -> list[dict[str, Any]]:
        recovered = []
        self.transactions_root.mkdir(parents=True, exist_ok=True)
        for path in self.transactions_root.glob("TXN-*.json"):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("state") in {"PENDING", "RUNNING", "FAILED"}:
                self.rollback_service.restore_files([Path(item) for item in payload.get("backup_targets", [])])
                payload["state"] = "ROLLED_BACK"
                path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                recovered.append(payload)
        return recovered

    def _audit(self, action: str, actor: str, role: str, entity_id: str, details: dict[str, Any]) -> None:
        if not self.audit_service:
            return
        self.audit_service.log_governance_event(
            actor=actor or "system",
            role=role or "system",
            action=action,
            entity_type="supply_order",
            entity_id=entity_id,
            details=details,
        )

    def _emit_event(self, event_type: str, **payload: Any) -> None:
        if not self.event_notification_service:
            return
        self.event_notification_service.emit(event_type, payload)
