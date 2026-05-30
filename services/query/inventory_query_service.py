from __future__ import annotations
from typing import Any

class InventoryQueryService:
    def __init__(self, drive_service, json_service, domain_paths_service=None) -> None:
        self.drive_service = drive_service
        self.json_service = json_service
        self.domain_paths = domain_paths_service

    def list_inventory_snapshot(self, manufacturer_code: str) -> dict[str, Any]:
        inventory_path = (
            self.domain_paths.shared_mandi_inventory_projection_path(manufacturer_code)
            if self.domain_paths
            else self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"
        )
        return self.json_service.read_json(inventory_path, {"items": []})

    def get_available_quantity(self, manufacturer_code: str, product_code: str) -> int:
        snapshot = self.list_inventory_snapshot(manufacturer_code)
        item = next((entry for entry in snapshot.get("items", []) if entry.get("product_code") == product_code or entry.get("product_id") == product_code), None)
        if not item:
            return 0
        mandi_inventory = item.get("mandi_inventory", {}) or {}
        return max(0, int(mandi_inventory.get("available_qty", 0)) - int(mandi_inventory.get("reserved_qty", 0)))
