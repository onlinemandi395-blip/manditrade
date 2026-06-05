from __future__ import annotations

from typing import Any


class DualInventoryService:
    def __init__(self, safe_drive_write_service, json_service, domain_paths_service, inventory_service=None) -> None:
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.domain_paths = domain_paths_service
        self.inventory_service = inventory_service

    def _default_doc(self, manufacturer_code: str) -> dict[str, Any]:
        return {"schema_version": "2.0", "manufacturer_code": manufacturer_code, "items": []}

    def list_inventory(self, manufacturer_code: str) -> dict[str, Any]:
        if self.inventory_service:
            self.inventory_service._sync_legacy_inventory_from_canonical(manufacturer_code)
        path = self.domain_paths.private_self_inventory_path(manufacturer_code)
        payload = self.json_service.read_json(path, self._default_doc(manufacturer_code))
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, payload, schema_name="inventory")
        return payload

    def upsert_inventory_item(
        self,
        manufacturer_code: str,
        *,
        product_id: str,
        product_name: str,
        unit: str,
        self_available_qty: int = 0,
        mandi_available_qty: int = 0,
        visible_to_mandi: bool = True,
    ) -> None:
        if self.inventory_service:
            self.inventory_service.sync_product_record(
                manufacturer_code=manufacturer_code,
                product_id=product_id,
                product_name=product_name,
                unit=unit,
                self_available_qty=int(self_available_qty),
                mandi_available_qty=int(mandi_available_qty),
                visible_to_mandi=bool(visible_to_mandi),
            )
            return
        raise ValueError("Inventory service is not configured.")

    def reserve_self_inventory(
        self,
        manufacturer_code: str,
        items: list[dict[str, Any]],
        *,
        related_order_id: str = "",
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        if self.inventory_service:
            self.inventory_service.reserve_order_items(
                owner_role="manufacturer",
                owner_id=manufacturer_code,
                item_type="PRODUCT",
                network="MARKETPLACE",
                items=items,
                related_order_id=related_order_id,
                created_by=created_by or manufacturer_code,
                note=note or "Marketplace/self inventory reserved",
            )
            return self.list_inventory(manufacturer_code)
        raise ValueError("Inventory service is not configured.")

    def reserve_mandi_inventory(
        self,
        manufacturer_code: str,
        items: list[dict[str, Any]],
        *,
        related_order_id: str = "",
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        if self.inventory_service:
            self.inventory_service.reserve_order_items(
                owner_role="manufacturer",
                owner_id=manufacturer_code,
                item_type="PRODUCT",
                network="MANDIPLACE",
                items=items,
                related_order_id=related_order_id,
                created_by=created_by or manufacturer_code,
                note=note or "Mandi inventory reserved",
            )
            return self.list_inventory(manufacturer_code)
        raise ValueError("Inventory service is not configured.")

    def release_reserved(
        self,
        manufacturer_code: str,
        items: list[dict[str, Any]],
        *,
        bucket: str,
        related_order_id: str = "",
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        if self.inventory_service:
            network = "MARKETPLACE" if bucket == "self_inventory" else "MANDIPLACE"
            self.inventory_service.release_order_reservations(
                owner_role="manufacturer",
                owner_id=manufacturer_code,
                item_type="PRODUCT",
                network=network,
                items=items,
                related_order_id=related_order_id,
                created_by=created_by or manufacturer_code,
                note=note or f"{bucket} reservation released",
            )
            return self.list_inventory(manufacturer_code)
        raise ValueError("Inventory service is not configured.")

    def finalize_reserved(
        self,
        manufacturer_code: str,
        items: list[dict[str, Any]],
        *,
        bucket: str,
        related_order_id: str = "",
        note: str = "",
        created_by: str = "",
    ) -> dict[str, Any]:
        if self.inventory_service:
            network = "MARKETPLACE" if bucket == "self_inventory" else "MANDIPLACE"
            self.inventory_service.confirm_order_items(
                owner_role="manufacturer",
                owner_id=manufacturer_code,
                item_type="PRODUCT",
                network=network,
                items=items,
                related_order_id=related_order_id,
                created_by=created_by or manufacturer_code,
                note=note or f"{bucket} reservation finalized",
            )
            return self.list_inventory(manufacturer_code)
        raise ValueError("Inventory service is not configured.")

    def transfer_self_to_mandi(self, manufacturer_code: str, product_id: str, qty: int) -> dict[str, Any]:
        if not self.inventory_service:
            raise ValueError("Inventory service is not configured.")
        self_inventory = self.inventory_service.get_inventory_by_keys(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            item_type="PRODUCT",
            item_id=product_id,
            network="MARKETPLACE",
        )
        mandi_inventory = self.inventory_service.get_inventory_by_keys(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            item_type="PRODUCT",
            item_id=product_id,
            network="MANDIPLACE",
        )
        if not self_inventory or not mandi_inventory:
            raise ValueError(f"Inventory record not found for {product_id}")
        self.inventory_service.adjust_stock(
            inventory_id=self_inventory["inventory_id"],
            qty_delta=-int(qty or 0),
            note="Transferred from self inventory to mandi inventory",
            created_by=manufacturer_code,
            movement_type="ADJUST",
        )
        self.inventory_service.adjust_stock(
            inventory_id=mandi_inventory["inventory_id"],
            qty_delta=int(qty or 0),
            note="Transferred from self inventory to mandi inventory",
            created_by=manufacturer_code,
            movement_type="ADD",
        )
        return self.list_inventory(manufacturer_code)

    def withdraw_mandi_to_self(self, manufacturer_code: str, product_id: str, qty: int) -> dict[str, Any]:
        if not self.inventory_service:
            raise ValueError("Inventory service is not configured.")
        mandi_inventory = self.inventory_service.get_inventory_by_keys(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            item_type="PRODUCT",
            item_id=product_id,
            network="MANDIPLACE",
        )
        self_inventory = self.inventory_service.get_inventory_by_keys(
            owner_role="manufacturer",
            owner_id=manufacturer_code,
            item_type="PRODUCT",
            item_id=product_id,
            network="MARKETPLACE",
        )
        if not self_inventory or not mandi_inventory:
            raise ValueError(f"Inventory record not found for {product_id}")
        self.inventory_service.adjust_stock(
            inventory_id=mandi_inventory["inventory_id"],
            qty_delta=-int(qty or 0),
            note="Withdrawn from mandi inventory to self inventory",
            created_by=manufacturer_code,
            movement_type="ADJUST",
        )
        self.inventory_service.adjust_stock(
            inventory_id=self_inventory["inventory_id"],
            qty_delta=int(qty or 0),
            note="Withdrawn from mandi inventory to self inventory",
            created_by=manufacturer_code,
            movement_type="ADD",
        )
        return self.list_inventory(manufacturer_code)
