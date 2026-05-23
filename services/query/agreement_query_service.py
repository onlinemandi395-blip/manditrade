from __future__ import annotations
from typing import Any

class AgreementQueryService:
    def __init__(self, drive_service, json_service) -> None:
        self.drive_service = drive_service
        self.json_service = json_service

    def list_agreements(self, manufacturer_code: str) -> list[dict[str, Any]]:
        agreements_path = self.drive_service.get_manufacturer_paths(manufacturer_code).shared_zone / "agreements.json"
        return self.json_service.read_json(agreements_path, {"agreements": []}).get("agreements", [])

    def get_agreement(self, manufacturer_code: str, agreement_id: str) -> dict[str, Any] | None:
        agreements = self.list_agreements(manufacturer_code)
        return next((a for a in agreements if a.get("agreement_id") == agreement_id), None)