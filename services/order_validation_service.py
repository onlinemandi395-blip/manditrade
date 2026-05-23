from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from services.drive_service import DriveService
from services.json_service import JsonService


class OrderValidationService:
    def __init__(self, drive_service: DriveService, safe_drive_write_service, id_allocator_service=None) -> None:
        self.drive_service = drive_service
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = JsonService()
        self.id_allocator_service = id_allocator_service

    def _inventory_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "inventory.json"

    def _procurement_path(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "procurement.json"

    def validate_inventory(self, manufacturer_code: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        inventory_path = self._inventory_path(manufacturer_code)
        inventory = self.json_service.read_json(inventory_path, {"items": []})
        issues: list[dict[str, Any]] = []
        for item in items:
            record = next((entry for entry in inventory.get("items", []) if entry.get("product_code") == item["product_id"]), None)
            available_qty = int(record.get("quantity", 0) - record.get("reserved_quantity", 0)) if record else 0
            if available_qty < int(item["qty"]):
                issues.append(
                    {
                        "product_id": item["product_id"],
                        "required_qty": int(item["qty"]),
                        "available_qty": max(available_qty, 0),
                        "shortage_qty": int(item["qty"]) - max(available_qty, 0),
                        "city": record.get("city", "") if record else "",
                    }
                )
        return {"valid": not issues, "issues": issues}

    def reserve_inventory(self, manufacturer_code: str, items: list[dict[str, Any]]) -> None:
        inventory_path = self._inventory_path(manufacturer_code)
        def mutator(inventory: dict[str, Any]) -> dict[str, Any]:
            inventory.setdefault("schema_version", "1.0")
            inventory.setdefault("manufacturer_code", manufacturer_code)
            inventory.setdefault("items", [])
            for item in items:
                record = next((entry for entry in inventory.get("items", []) if entry.get("product_code") == item["product_id"]), None)
                if not record:
                    continue
                record["reserved_quantity"] = int(record.get("reserved_quantity", 0)) + int(item["qty"])
            return inventory
        self.safe_drive_write_service.mutate_json(inventory_path, mutator, schema_name="inventory")

    def create_procurement_requests(
        self,
        manufacturer_code: str,
        shortages: list[dict[str, Any]],
        requested_by_city: str,
    ) -> list[dict[str, Any]]:
        procurement_path = self._procurement_path(manufacturer_code)
        created: list[dict[str, Any]] = []
        def mutator(procurement: dict[str, Any]) -> dict[str, Any]:
            procurement.setdefault("schema_version", "1.0")
            procurement.setdefault("manufacturer_code", manufacturer_code)
            procurement.setdefault("requests", [])
            for issue in shortages:
                request = {
                    "request_id": self.id_allocator_service.allocate("procurement") if self.id_allocator_service else f"REQ-{datetime.now(UTC).year}-{len(created)+1:06d}",
                    "product_id": issue["product_id"],
                    "required_qty": issue["shortage_qty"],
                    "requested_by": manufacturer_code,
                    "city": requested_by_city,
                    "status": "OPEN",
                    "created_at": datetime.now(UTC).isoformat(),
                }
                procurement["requests"].append(request)
                created.append(request)
            return procurement
        self.safe_drive_write_service.mutate_json(procurement_path, mutator, schema_name="procurement")
        return created
