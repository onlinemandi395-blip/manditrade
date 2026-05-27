from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class TradeConfirmationService:
    def __init__(self, safe_drive_write_service, json_service, id_allocator_service, domain_paths_service) -> None:
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.domain_paths = domain_paths_service

    def create_confirmation(
        self,
        manufacturer_code: str,
        *,
        source_type: str,
        source_id: str,
        confirmed_by: str,
        accepted_terms_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        path = self.domain_paths.confirmations_path(manufacturer_code)
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, {"schema_version": "2.0", "confirmations": []})
        confirmation = {
            "confirmation_id": self.id_allocator_service.allocate("confirmation"),
            "source_type": source_type,
            "source_id": source_id,
            "confirmed_by": confirmed_by,
            "accepted_terms_snapshot": accepted_terms_snapshot,
            "confirmed_at": datetime.now(UTC).isoformat(),
        }
        self.safe_drive_write_service.append_record(path, "confirmations", confirmation)
        return confirmation
