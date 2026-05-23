from __future__ import annotations
from typing import Any

class InventoryQueryService:
    def __init__(self, drive_service, json_service) -> None:
        self.drive_service = drive_service
        self.json_service = json_service

    def list_inventory_snapshot(self, manufacturer_code: str) -> dict[str, Any]:
        inventory_path = self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"
        return self.json_service.read_json(inventory_path, {"items": []})

    def get_available_quantity(self, manufacturer_code: str, product_code: str) -> int:
        snapshot = self.list_inventory_snapshot(manufacturer_code)
        item = next((entry for entry in snapshot.get("items", []) if entry.get("product_code") == product_code), None)
        if not item:
            return 0
        return max(0, int(item.get("quantity", 0)) - int(item.get("reserved_quantity", 0)))