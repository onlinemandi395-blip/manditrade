from __future__ import annotations
from typing import Any

class ProcurementQueryService:
    def __init__(self, drive_service, json_service) -> None:
        self.drive_service = drive_service
        self.json_service = json_service

    def list_procurement_requests(self, manufacturer_code: str) -> list[dict[str, Any]]:
        procurement_path = self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "procurement.json"
        return self.json_service.read_json(procurement_path, {"requests": []}).get("requests", [])