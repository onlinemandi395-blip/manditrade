from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class InventoryService:
    NETWORK_FILE_MAP = {
        "MARKETPLACE": "manufacturer_inventory",
        "MANDIPLACE": "mandiplace_inventory",
        "RAW_MATERIALS": "raw_material_inventory",
        "SUTA_MANDI": "suta_inventory",
    }
    NETWORK_ITEM_TYPES = {
        "MARKETPLACE": "PRODUCT",
        "MANDIPLACE": "PRODUCT",
        "RAW_MATERIALS": "RAW_MATERIAL",
        "SUTA_MANDI": "SUTA",
    }

    def __init__(
        self,
        *,
        drive_path_service,
        domain_paths_service,
        safe_drive_write_service,
        json_service,
        id_allocator_service,
        governance_service=None,
        event_notification_service=None,
    ) -> None:
        self.drive_path_service = drive_path_service
        self.domain_paths = domain_paths_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.governance_service = governance_service
        self.event_notification_service = event_notification_service

    def create_inventory_record(
        self,
        *,
        owner_role: str,
        owner_id: str,
        warehouse_id: str = "",
        item_type: str,
        item_id: str,
        network: str,
        available_qty: int = 0,
        reserved_qty: int = 0,
        packed_qty: int = 0,
        dispatched_qty: int = 0,
        delivered_qty: int = 0,
        sold_qty: int = 0,
        damaged_qty: int = 0,
        returned_qty: int = 0,
        unit: str = "",
        location: dict[str, Any] | None = None,
        reorder_level: int = 0,
        status: str = "ACTIVE",
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        normalized_network = self._network(network)
        path = self._inventory_path(normalized_network)
        record = self._build_record(
            owner_role=owner_role,
            owner_id=owner_id,
            warehouse_id=warehouse_id,
            item_type=item_type,
            item_id=item_id,
            network=normalized_network,
            available_qty=available_qty,
            reserved_qty=reserved_qty,
            packed_qty=packed_qty,
            dispatched_qty=dispatched_qty,
            delivered_qty=delivered_qty,
            sold_qty=sold_qty,
            damaged_qty=damaged_qty,
            returned_qty=returned_qty,
            unit=unit,
            location=location or {},
            reorder_level=reorder_level,
            status=status,
        )

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("items", [])
            existing = next((item for item in payload["items"] if item.get("inventory_id") == record["inventory_id"]), None)
            if existing:
                existing.update(record)
            else:
                payload["items"].append(record)
            payload["updated_at"] = self._now()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        if note:
            self._log_movement(
                inventory_id=record["inventory_id"],
                warehouse_id=record.get("warehouse_id", ""),
                movement_type="ADD",
                qty=max(int(available_qty or 0), 0),
                before_qty=0,
                after_qty=max(int(available_qty or 0), 0),
                related_order_id="",
                note=note,
                created_by=created_by,
            )
        self._sync_legacy_projection(record)
        return record

    def adjust_stock(
        self,
        *,
        inventory_id: str,
        qty_delta: int,
        note: str,
        created_by: str,
        movement_type: str = "ADJUST",
        related_order_id: str = "",
    ) -> dict[str, Any]:
        if movement_type == "ADJUST" and not note.strip():
            raise ValueError("Admin stock adjustment requires an audit note.")
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        before_qty = int(record.get("available_qty", 0) or 0)
        after_qty = before_qty + int(qty_delta or 0)
        if after_qty < 0:
            raise ValueError("Available stock cannot go negative.")

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["available_qty"] = after_qty
                    if movement_type == "DAMAGE":
                        item["damaged_qty"] = max(0, int(item.get("damaged_qty", 0) or 0) + abs(int(qty_delta or 0)))
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type=movement_type,
            qty=abs(int(qty_delta or 0)),
            before_qty=before_qty,
            after_qty=after_qty,
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        updated = self.get_inventory_record(inventory_id)
        self._sync_legacy_projection(updated)
        self._emit_inventory_event(updated, "STOCK_ADJUSTED", note=note)
        return updated

    def reserve_stock(self, *, inventory_id: str, qty: int, related_order_id: str = "", note: str = "", created_by: str = "") -> dict[str, Any]:
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        requested = max(int(qty or 0), 0)
        if requested <= 0:
            raise ValueError("Reservation quantity must be positive.")
        before_available = int(record.get("available_qty", 0) or 0)
        before_reserved = int(record.get("reserved_qty", 0) or 0)
        if before_available < requested:
            raise ValueError("Insufficient available stock for reservation.")

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["available_qty"] = before_available - requested
                    item["reserved_qty"] = before_reserved + requested
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type="RESERVE",
            qty=requested,
            before_qty=before_available,
            after_qty=before_available - requested,
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        updated = self.get_inventory_record(inventory_id)
        self._sync_legacy_projection(updated)
        self._emit_inventory_event(updated, "STOCK_RESERVED", note=note)
        return updated

    def release_reservation(self, *, inventory_id: str, qty: int, related_order_id: str = "", note: str = "", created_by: str = "") -> dict[str, Any]:
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        requested = max(int(qty or 0), 0)
        if requested <= 0:
            raise ValueError("Release quantity must be positive.")
        before_available = int(record.get("available_qty", 0) or 0)
        before_reserved = int(record.get("reserved_qty", 0) or 0)
        if before_reserved < requested:
            raise ValueError("Cannot release more stock than currently reserved.")

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["available_qty"] = before_available + requested
                    item["reserved_qty"] = before_reserved - requested
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type="RELEASE",
            qty=requested,
            before_qty=before_available,
            after_qty=before_available + requested,
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        updated = self.get_inventory_record(inventory_id)
        self._sync_legacy_projection(updated)
        self._emit_inventory_event(updated, "STOCK_RELEASED", note=note)
        return updated

    def confirm_sale(self, *, inventory_id: str, qty: int, related_order_id: str = "", note: str = "", created_by: str = "") -> dict[str, Any]:
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        requested = max(int(qty or 0), 0)
        before_reserved = int(record.get("reserved_qty", 0) or 0)
        before_sold = int(record.get("sold_qty", 0) or 0)
        if before_reserved < requested:
            raise ValueError("Cannot confirm sale for more stock than reserved.")

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["reserved_qty"] = before_reserved - requested
                    item["sold_qty"] = before_sold + requested
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type="SELL",
            qty=requested,
            before_qty=int(record.get("available_qty", 0) or 0),
            after_qty=int(record.get("available_qty", 0) or 0),
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        updated = self.get_inventory_record(inventory_id)
        self._sync_legacy_projection(updated)
        return updated

    def mark_packed(self, *, inventory_id: str, qty: int, related_order_id: str = "", note: str = "", created_by: str = "") -> dict[str, Any]:
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        requested = max(int(qty or 0), 0)
        before_packed = int(record.get("packed_qty", 0) or 0)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["packed_qty"] = before_packed + requested
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type="PACK",
            qty=requested,
            before_qty=int(record.get("available_qty", 0) or 0),
            after_qty=int(record.get("available_qty", 0) or 0),
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        return self.get_inventory_record(inventory_id)

    def mark_dispatched(self, *, inventory_id: str, qty: int, related_order_id: str = "", note: str = "", created_by: str = "") -> dict[str, Any]:
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        requested = max(int(qty or 0), 0)
        before_dispatched = int(record.get("dispatched_qty", 0) or 0)
        before_packed = int(record.get("packed_qty", 0) or 0)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["dispatched_qty"] = before_dispatched + requested
                    item["packed_qty"] = max(0, before_packed - requested)
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        record = self.get_inventory_record(inventory_id)
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type="DISPATCH",
            qty=requested,
            before_qty=int(record.get("available_qty", 0) or 0),
            after_qty=int(record.get("available_qty", 0) or 0),
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        self._emit_inventory_event(record, "STOCK_DISPATCHED", note=note)
        return record

    def mark_received(self, *, inventory_id: str, qty: int, related_order_id: str = "", note: str = "", created_by: str = "") -> dict[str, Any]:
        record, network = self._find_inventory_record(inventory_id)
        path = self._inventory_path(network)
        requested = max(int(qty or 0), 0)
        before_dispatched = int(record.get("dispatched_qty", 0) or 0)
        before_delivered = int(record.get("delivered_qty", 0) or 0)

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("items", []):
                if item.get("inventory_id") == inventory_id:
                    item["dispatched_qty"] = max(0, before_dispatched - requested)
                    item["delivered_qty"] = before_delivered + requested
                    item["updated_at"] = self._now()
                    payload["updated_at"] = self._now()
                    return payload
            raise ValueError(f"Inventory record not found: {inventory_id}")

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        record = self.get_inventory_record(inventory_id)
        self._log_movement(
            inventory_id=inventory_id,
            warehouse_id=record.get("warehouse_id", ""),
            movement_type="RECEIVE",
            qty=requested,
            before_qty=int(record.get("available_qty", 0) or 0),
            after_qty=int(record.get("available_qty", 0) or 0),
            related_order_id=related_order_id,
            note=note,
            created_by=created_by,
        )
        self._emit_inventory_event(record, "STOCK_RECEIVED", note=note)
        return record

    def get_inventory_for_owner(self, *, owner_role: str, owner_id: str, network: str | None = None) -> list[dict[str, Any]]:
        records = self.list_inventory_records(network=network)
        return [item for item in records if item.get("owner_role") == owner_role and item.get("owner_id") == owner_id]

    def get_inventory_for_network(self, network: str) -> list[dict[str, Any]]:
        return self.list_inventory_records(network=network)

    def get_low_stock_items(self, *, network: str | None = None) -> list[dict[str, Any]]:
        records = self.list_inventory_records(network=network)
        return [
            item
            for item in records
            if str(item.get("status", "ACTIVE")).upper() == "ACTIVE"
            and int(item.get("available_qty", 0) or 0) <= int(item.get("reorder_level", 0) or 0)
        ]

    def stock_status(self, inventory: dict[str, Any] | None) -> str:
        if not inventory:
            return "OUT_OF_STOCK"
        available = int(inventory.get("available_qty", 0) or 0)
        reorder = int(inventory.get("reorder_level", 0) or 0)
        if available <= 0:
            return "OUT_OF_STOCK"
        if reorder and available <= reorder:
            return "LOW_STOCK"
        return "IN_STOCK"

    def sync_product_record(
        self,
        *,
        manufacturer_code: str,
        product_id: str,
        product_name: str,
        unit: str,
        self_available_qty: int,
        mandi_available_qty: int,
        visible_to_mandi: bool = True,
    ) -> None:
        warehouse = self.governance_service.ensure_default_warehouse(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            warehouse_name=f"{product_name} Hub",
        ) if self.governance_service else {"warehouse_id": ""}
        marketplace = self._find_inventory_by_keys(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            warehouse_id=str(warehouse.get("warehouse_id", "")),
            item_type="PRODUCT",
            item_id=product_id,
            network="MARKETPLACE",
        )
        mandiplace = self._find_inventory_by_keys(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            warehouse_id=str(warehouse.get("warehouse_id", "")),
            item_type="PRODUCT",
            item_id=product_id,
            network="MANDIPLACE",
        )
        self._upsert_inventory_snapshot(
            existing=marketplace,
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            warehouse_id=str(warehouse.get("warehouse_id", "")),
            item_type="PRODUCT",
            item_id=product_id,
            network="MARKETPLACE",
            available_qty=self_available_qty,
            reserved_qty=int((marketplace or {}).get("reserved_qty", 0) or 0),
            packed_qty=int((marketplace or {}).get("packed_qty", 0) or 0),
            dispatched_qty=int((marketplace or {}).get("dispatched_qty", 0) or 0),
            delivered_qty=int((marketplace or {}).get("delivered_qty", 0) or 0),
            sold_qty=int((marketplace or {}).get("sold_qty", 0) or 0),
            damaged_qty=int((marketplace or {}).get("damaged_qty", 0) or 0),
            returned_qty=int((marketplace or {}).get("returned_qty", 0) or 0),
            unit=unit,
            reorder_level=5,
            status="ACTIVE",
            location={"warehouse_name": product_name},
        )
        self._upsert_inventory_snapshot(
            existing=mandiplace,
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            warehouse_id=str(warehouse.get("warehouse_id", "")),
            item_type="PRODUCT",
            item_id=product_id,
            network="MANDIPLACE",
            available_qty=mandi_available_qty,
            reserved_qty=int((mandiplace or {}).get("reserved_qty", 0) or 0),
            packed_qty=int((mandiplace or {}).get("packed_qty", 0) or 0),
            dispatched_qty=int((mandiplace or {}).get("dispatched_qty", 0) or 0),
            delivered_qty=int((mandiplace or {}).get("delivered_qty", 0) or 0),
            sold_qty=int((mandiplace or {}).get("sold_qty", 0) or 0),
            damaged_qty=int((mandiplace or {}).get("damaged_qty", 0) or 0),
            returned_qty=int((mandiplace or {}).get("returned_qty", 0) or 0),
            unit=unit,
            reorder_level=5,
            status="ACTIVE" if visible_to_mandi else "HIDDEN",
            location={"warehouse_name": product_name},
        )
        self._sync_legacy_inventory_from_canonical(manufacturer_code)

    def sync_raw_material_record(self, item: dict[str, Any]) -> dict[str, Any]:
        network = "SUTA_MANDI" if str(item.get("category", "")).strip().upper() == "SUTA" else "RAW_MATERIALS"
        item_type = self.NETWORK_ITEM_TYPES[network]
        owner_id = str(item.get("mahajan_id", "")).strip()
        warehouse = self.governance_service.ensure_default_warehouse(
            owner_role="mahajan",
            owner_id=owner_id,
            warehouse_name=f"{str(item.get('name', '')).strip() or owner_id} Godown",
            city=str(item.get("city", "")).strip(),
        ) if self.governance_service and owner_id else {"warehouse_id": ""}
        existing = self._find_inventory_by_keys(
            owner_role="mahajan",
            owner_id=owner_id,
            warehouse_id=str(warehouse.get("warehouse_id", "")),
            item_type=item_type,
            item_id=str(item.get("raw_material_id", "")).strip(),
            network=network,
        )
        return self._upsert_inventory_snapshot(
            existing=existing,
            owner_role="mahajan",
            owner_id=owner_id,
            warehouse_id=str(warehouse.get("warehouse_id", "")),
            item_type=item_type,
            item_id=str(item.get("raw_material_id", "")).strip(),
            network=network,
            available_qty=int(item.get("available_qty", 0) or 0),
            reserved_qty=int((existing or {}).get("reserved_qty", 0) or 0),
            packed_qty=int((existing or {}).get("packed_qty", 0) or 0),
            dispatched_qty=int((existing or {}).get("dispatched_qty", 0) or 0),
            delivered_qty=int((existing or {}).get("delivered_qty", 0) or 0),
            sold_qty=int((existing or {}).get("sold_qty", 0) or 0),
            damaged_qty=int((existing or {}).get("damaged_qty", 0) or 0),
            returned_qty=int((existing or {}).get("returned_qty", 0) or 0),
            unit=str(item.get("unit", "kg")),
            reorder_level=10,
            status=str(item.get("status", "ACTIVE")),
            location={"warehouse_name": str(item.get("name", "")), "city": str(item.get("city", ""))},
        )

    def sync_raw_material_catalog(self, items: list[dict[str, Any]]) -> None:
        for item in items:
            self.sync_raw_material_record(item)

    def list_inventory_records(self, *, network: str | None = None) -> list[dict[str, Any]]:
        if network:
            path = self._inventory_path(self._network(network))
            return self.json_service.read_json(path, self._inventory_doc()).get("items", [])
        rows: list[dict[str, Any]] = []
        for network_name in self.NETWORK_FILE_MAP:
            rows.extend(self.json_service.read_json(self._inventory_path(network_name), self._inventory_doc()).get("items", []))
        return rows

    def get_inventory_record(self, inventory_id: str) -> dict[str, Any]:
        record, _network = self._find_inventory_record(inventory_id)
        return record

    def get_inventory_by_keys(
        self,
        *,
        owner_role: str,
        owner_id: str,
        warehouse_id: str | None = None,
        item_type: str,
        item_id: str,
        network: str,
    ) -> dict[str, Any] | None:
        return self._find_inventory_by_keys(
            owner_role=owner_role,
            owner_id=owner_id,
            warehouse_id=warehouse_id,
            item_type=item_type,
            item_id=item_id,
            network=network,
        )

    def aggregate_inventory(
        self,
        *,
        owner_role: str,
        owner_id: str,
        item_type: str,
        item_id: str,
        network: str,
    ) -> dict[str, Any] | None:
        rows = [
            row
            for row in self.get_inventory_for_network(network)
            if row.get("owner_role") == str(owner_role or "").strip().lower()
            and row.get("owner_id") == str(owner_id or "").strip()
            and row.get("item_type") == str(item_type or "").strip().upper()
            and row.get("item_id") == str(item_id or "").strip()
        ]
        if not rows:
            return None
        first = dict(rows[0])
        first["warehouse_id"] = ""
        for field in ("available_qty", "reserved_qty", "packed_qty", "dispatched_qty", "delivered_qty", "sold_qty", "damaged_qty", "returned_qty"):
            first[field] = sum(int(item.get(field, 0) or 0) for item in rows)
        return first

    def warehouse_inventory_options(
        self,
        *,
        owner_role: str,
        owner_id: str,
        item_type: str,
        item_id: str,
        network: str,
    ) -> list[dict[str, Any]]:
        rows = self.get_inventory_for_network(network)
        return [
            row
            for row in rows
            if row.get("owner_role") == str(owner_role or "").strip().lower()
            and row.get("owner_id") == str(owner_id or "").strip()
            and row.get("item_type") == str(item_type or "").strip().upper()
            and row.get("item_id") == str(item_id or "").strip()
        ]

    def get_marketplace_inventory_for_product(self, product: dict[str, Any]) -> dict[str, Any] | None:
        seller_id = str(product.get("public_seller_manufacturer_id") or product.get("created_by_manufacturer_id") or product.get("created_by") or "").strip()
        product_id = str(product.get("product_id", "")).strip()
        if not seller_id or not product_id:
            return None
        return self.aggregate_inventory(
            owner_role="manufacturer",
            owner_id=seller_id,
            item_type="PRODUCT",
            item_id=product_id,
            network="MARKETPLACE",
        )

    def get_mandiplace_inventory_for_product(self, manufacturer_code: str, product_id: str) -> dict[str, Any] | None:
        return self.aggregate_inventory(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            item_type="PRODUCT",
            item_id=product_id,
            network="MANDIPLACE",
        )

    def get_raw_material_inventory(self, raw_material_id: str, *, network: str | None = None) -> dict[str, Any] | None:
        target_networks = [self._network(network)] if network else ["RAW_MATERIALS", "SUTA_MANDI"]
        for network_name in target_networks:
            for item in self.get_inventory_for_network(network_name):
                if item.get("item_id") == raw_material_id:
                    return item
        return None

    def movement_history(self, *, inventory_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.json_service.read_json(self._movement_path(), {"movements": []}).get("movements", [])
        if inventory_id:
            rows = [item for item in rows if item.get("inventory_id") == inventory_id]
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows

    def release_order_reservations(self, *, owner_role: str, owner_id: str, item_type: str, network: str, items: list[dict[str, Any]], related_order_id: str, created_by: str = "", note: str = "") -> None:
        for item in items:
            record = self.get_inventory_by_keys(
                owner_role=owner_role,
                owner_id=owner_id,
                item_type=item_type,
                item_id=str(item.get("product_id") or item.get("raw_material_id") or item.get("item_id") or ""),
                network=network,
            )
            if record:
                self.release_reservation(
                    inventory_id=record["inventory_id"],
                    qty=int(float(item.get("qty", 0) or 0)),
                    related_order_id=related_order_id,
                    note=note,
                    created_by=created_by,
                )

    def reserve_order_items(self, *, owner_role: str, owner_id: str, item_type: str, network: str, items: list[dict[str, Any]], related_order_id: str, created_by: str = "", note: str = "") -> None:
        for item in items:
            record = self.get_inventory_by_keys(
                owner_role=owner_role,
                owner_id=owner_id,
                item_type=item_type,
                item_id=str(item.get("product_id") or item.get("raw_material_id") or item.get("item_id") or ""),
                network=network,
            )
            if not record:
                raise ValueError(f"Inventory record not found for {item.get('product_id') or item.get('raw_material_id') or item.get('item_id')}")
            self.reserve_stock(
                inventory_id=record["inventory_id"],
                qty=int(float(item.get("qty", 0) or 0)),
                related_order_id=related_order_id,
                note=note,
                created_by=created_by,
            )

    def confirm_order_items(self, *, owner_role: str, owner_id: str, item_type: str, network: str, items: list[dict[str, Any]], related_order_id: str, created_by: str = "", note: str = "") -> None:
        for item in items:
            record = self.get_inventory_by_keys(
                owner_role=owner_role,
                owner_id=owner_id,
                item_type=item_type,
                item_id=str(item.get("product_id") or item.get("raw_material_id") or item.get("item_id") or ""),
                network=network,
            )
            if not record:
                raise ValueError(f"Inventory record not found for {item.get('product_id') or item.get('raw_material_id') or item.get('item_id')}")
            self.confirm_sale(
                inventory_id=record["inventory_id"],
                qty=int(float(item.get("qty", 0) or 0)),
                related_order_id=related_order_id,
                note=note,
                created_by=created_by,
            )

    def _build_record(
        self,
        *,
        owner_role: str,
        owner_id: str,
        warehouse_id: str,
        item_type: str,
        item_id: str,
        network: str,
        available_qty: int,
        reserved_qty: int,
        packed_qty: int,
        dispatched_qty: int,
        delivered_qty: int,
        sold_qty: int,
        damaged_qty: int,
        returned_qty: int,
        unit: str,
        location: dict[str, Any],
        reorder_level: int,
        status: str,
        inventory_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        now = self._now()
        return {
            "inventory_id": inventory_id or self.id_allocator_service.allocate("inventory"),
            "owner_role": str(owner_role or "").strip().lower(),
            "owner_id": str(owner_id or "").strip(),
            "warehouse_id": str(warehouse_id or "").strip().upper(),
            "item_type": str(item_type or "").strip().upper(),
            "item_id": str(item_id or "").strip(),
            "network": network,
            "available_qty": max(int(available_qty or 0), 0),
            "reserved_qty": max(int(reserved_qty or 0), 0),
            "packed_qty": max(int(packed_qty or 0), 0),
            "dispatched_qty": max(int(dispatched_qty or 0), 0),
            "delivered_qty": max(int(delivered_qty or 0), 0),
            "sold_qty": max(int(sold_qty or 0), 0),
            "damaged_qty": max(int(damaged_qty or 0), 0),
            "returned_qty": max(int(returned_qty or 0), 0),
            "unit": str(unit or "").strip(),
            "location": {
                "city": str((location or {}).get("city", "")).strip(),
                "state": str((location or {}).get("state", "")).strip(),
                "pincode": str((location or {}).get("pincode", "")).strip(),
                "warehouse_name": str((location or {}).get("warehouse_name", "")).strip(),
            },
            "reorder_level": max(int(reorder_level or 0), 0),
            "status": str(status or "ACTIVE").strip().upper(),
            "created_at": created_at or now,
            "updated_at": now,
        }

    def _upsert_inventory_snapshot(
        self,
        *,
        existing: dict[str, Any] | None,
        owner_role: str,
        owner_id: str,
        warehouse_id: str,
        item_type: str,
        item_id: str,
        network: str,
        available_qty: int,
        reserved_qty: int,
        packed_qty: int,
        dispatched_qty: int,
        delivered_qty: int,
        sold_qty: int,
        damaged_qty: int,
        returned_qty: int,
        unit: str,
        reorder_level: int,
        status: str,
        location: dict[str, Any],
    ) -> dict[str, Any]:
        path = self._inventory_path(network)
        record = self._build_record(
            owner_role=owner_role,
            owner_id=owner_id,
            warehouse_id=warehouse_id,
            item_type=item_type,
            item_id=item_id,
            network=network,
            available_qty=available_qty,
            reserved_qty=reserved_qty,
            packed_qty=packed_qty,
            dispatched_qty=dispatched_qty,
            delivered_qty=delivered_qty,
            sold_qty=sold_qty,
            damaged_qty=damaged_qty,
            returned_qty=returned_qty,
            unit=unit,
            location=location,
            reorder_level=reorder_level,
            status=status,
            inventory_id=(existing or {}).get("inventory_id"),
            created_at=(existing or {}).get("created_at"),
        )

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("items", [])
            matched = next((item for item in payload["items"] if item.get("inventory_id") == record["inventory_id"]), None)
            if matched:
                matched.update(record)
            else:
                payload["items"].append(record)
            payload["updated_at"] = self._now()
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator, schema_name="inventory")
        return record

    def _inventory_path(self, network: str) -> Path:
        logical_name = self.NETWORK_FILE_MAP[self._network(network)]
        path = self.drive_path_service.path(f"inventory.{logical_name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _movement_path(self) -> Path:
        path = self.drive_path_service.path("inventory.movements")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _inventory_doc(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "items": [], "updated_at": ""}

    def _find_inventory_record(self, inventory_id: str) -> tuple[dict[str, Any], str]:
        for network_name in self.NETWORK_FILE_MAP:
            rows = self.get_inventory_for_network(network_name)
            item = next((row for row in rows if row.get("inventory_id") == inventory_id), None)
            if item:
                return item, network_name
        raise ValueError(f"Inventory record not found: {inventory_id}")

    def _find_inventory_by_keys(
        self,
        *,
        owner_role: str,
        owner_id: str,
        warehouse_id: str | None = None,
        item_type: str,
        item_id: str,
        network: str,
    ) -> dict[str, Any] | None:
        normalized_network = self._network(network)
        rows = self.get_inventory_for_network(normalized_network)
        return next(
            (
                row
                for row in rows
                if row.get("owner_role") == str(owner_role or "").strip().lower()
                and row.get("owner_id") == str(owner_id or "").strip()
                and (warehouse_id is None or row.get("warehouse_id") == str(warehouse_id or "").strip().upper())
                and row.get("item_type") == str(item_type or "").strip().upper()
                and row.get("item_id") == str(item_id or "").strip()
            ),
            None,
        )

    def _log_movement(
        self,
        *,
        inventory_id: str,
        warehouse_id: str,
        movement_type: str,
        qty: int,
        before_qty: int,
        after_qty: int,
        related_order_id: str,
        note: str,
        created_by: str,
    ) -> None:
        movement = {
            "movement_id": self.id_allocator_service.allocate("inventory_movement"),
            "inventory_id": inventory_id,
            "warehouse_id": str(warehouse_id or "").strip().upper(),
            "movement_type": str(movement_type or "").strip().upper(),
            "qty": max(int(qty or 0), 0),
            "before_qty": max(int(before_qty or 0), 0),
            "after_qty": max(int(after_qty or 0), 0),
            "related_order_id": str(related_order_id or "").strip(),
            "note": str(note or "").strip(),
            "created_by": str(created_by or "").strip(),
            "created_at": self._now(),
        }

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("movements", [])
            payload["movements"].append(movement)
            payload["updated_at"] = self._now()
            return payload

        self.safe_drive_write_service.mutate_json(self._movement_path(), mutator, schema_name="inventory")

    def _network(self, network: str) -> str:
        normalized = str(network or "").strip().upper()
        if normalized not in self.NETWORK_FILE_MAP:
            raise ValueError(f"Unsupported inventory network: {network}")
        return normalized

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _sync_legacy_projection(self, record: dict[str, Any]) -> None:
        if record.get("owner_role") != "manufacturer" or record.get("item_type") != "PRODUCT":
            return
        self._sync_legacy_inventory_from_canonical(record.get("owner_id", ""))

    def _sync_legacy_inventory_from_canonical(self, manufacturer_code: str) -> None:
        if not manufacturer_code:
            return
        marketplace_rows = self.get_inventory_for_owner(owner_role="manufacturer", owner_id=manufacturer_code, network="MARKETPLACE")
        mandi_rows = self.get_inventory_for_owner(owner_role="manufacturer", owner_id=manufacturer_code, network="MANDIPLACE")
        mandi_index: dict[str, list[dict[str, Any]]] = {}
        for item in mandi_rows:
            mandi_index.setdefault(str(item.get("item_id", "")), []).append(item)
        marketplace_index: dict[str, list[dict[str, Any]]] = {}
        for item in marketplace_rows:
            marketplace_index.setdefault(str(item.get("item_id", "")), []).append(item)
        payload = {"schema_version": "2.0", "manufacturer_code": manufacturer_code, "items": []}
        for product_id, grouped_market_rows in marketplace_index.items():
            grouped_mandi_rows = mandi_index.get(product_id, [])
            total_market_available = sum(int(row.get("available_qty", 0) or 0) for row in grouped_market_rows)
            total_market_reserved = sum(int(row.get("reserved_qty", 0) or 0) for row in grouped_market_rows)
            total_mandi_available = sum(int(row.get("available_qty", 0) or 0) for row in grouped_mandi_rows)
            total_mandi_reserved = sum(int(row.get("reserved_qty", 0) or 0) for row in grouped_mandi_rows)
            base_row = grouped_market_rows[0]
            payload["items"].append(
                {
                    "manufacturer_id": manufacturer_code,
                    "product_id": product_id,
                    "product_name": (base_row.get("location", {}) or {}).get("warehouse_name", product_id),
                    "self_inventory": {
                        "available_qty": total_market_available,
                        "reserved_qty": total_market_reserved,
                        "unit": base_row.get("unit", ""),
                    },
                    "mandi_inventory": {
                        "available_qty": total_mandi_available,
                        "reserved_qty": total_mandi_reserved,
                        "unit": (grouped_mandi_rows[0] if grouped_mandi_rows else {}).get("unit", base_row.get("unit", "")),
                        "visible_to_mandi": any(str(item.get("status", "ACTIVE")).upper() == "ACTIVE" for item in grouped_mandi_rows) if grouped_mandi_rows else False,
                    },
                }
            )
        legacy_path = self.domain_paths.private_self_inventory_path(manufacturer_code)
        self.safe_drive_write_service.replace_document(legacy_path, payload, schema_name="inventory")
        projection_path = self.domain_paths.shared_mandi_inventory_projection_path(manufacturer_code)
        projection = {
            "schema_version": "2.0",
            "manufacturer_code": manufacturer_code,
            "items": [
                {
                    "manufacturer_id": manufacturer_code,
                    "product_id": row.get("product_id", ""),
                    "product_name": row.get("product_name", ""),
                    "mandi_inventory": row.get("mandi_inventory", {}),
                }
                for row in payload.get("items", [])
            ],
        }
        self.safe_drive_write_service.replace_document(projection_path, projection, schema_name="inventory")

    def _emit_inventory_event(self, record: dict[str, Any], event_type: str, *, note: str = "") -> None:
        if not self.event_notification_service:
            return
        self.event_notification_service.emit(
            event_type,
            {
                "entity_type": "INVENTORY",
                "entity_id": record.get("inventory_id", ""),
                "title": event_type.replace("_", " ").title(),
                "message": note or f"Inventory event {event_type} for {record.get('item_id', '')}.",
                "manufacturer_code": record.get("owner_id", "") if record.get("owner_role") == "manufacturer" else "",
                "mahajan_id": record.get("owner_id", "") if record.get("owner_role") == "mahajan" else "",
            },
        )
