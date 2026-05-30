from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class PublicBuyerService:
    def __init__(self, public_buyers_root: Path, safe_drive_write_service, json_service, id_allocator_service) -> None:
        self.public_buyers_root = public_buyers_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service

    @property
    def index_path(self) -> Path:
        return self.public_buyers_root / "index.json"

    def ensure_files(self) -> None:
        self.public_buyers_root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.safe_drive_write_service.replace_document(
                self.index_path,
                {"schema_version": "1.0", "buyers": []},
            )

    def profile_path(self, public_buyer_id: str) -> Path:
        return self.public_buyers_root / f"{public_buyer_id}.json"

    def notifications_path(self, public_buyer_id: str) -> Path:
        return self.public_buyers_root / public_buyer_id / "notifications.json"

    def cart_path(self, public_buyer_id: str) -> Path:
        return self.public_buyers_root / public_buyer_id / "cart.json"

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        self.ensure_files()
        email_key = email.strip().lower()
        index = self.json_service.read_json(self.index_path, {"buyers": []}).get("buyers", [])
        buyer = next((item for item in index if item.get("email", "").strip().lower() == email_key), None)
        if not buyer:
            return None
        return self.get_by_id(buyer["public_buyer_id"])

    def get_by_id(self, public_buyer_id: str) -> dict[str, Any] | None:
        self.ensure_files()
        path = self.profile_path(public_buyer_id)
        if not path.exists():
            return None
        return self.json_service.read_json(path, {})

    def register_or_get(self, *, email: str, full_name: str = "") -> dict[str, Any]:
        existing = self.get_by_email(email)
        if existing:
            return existing
        now = datetime.now(UTC).isoformat()
        public_buyer_id = self.id_allocator_service.allocate("public_buyer")
        profile = {
            "schema_version": "1.0",
            "public_buyer_id": public_buyer_id,
            "email": email.strip().lower(),
            "full_name": full_name.strip(),
            "mobile": "",
            "alternate_mobile": "",
            "address": {
                "line1": "",
                "line2": "",
                "city": "",
                "state": "",
                "pin_code": "",
                "landmark": "",
            },
            "delivery_instructions": "",
            "status": "ACTIVE",
            "created_at": now,
            "updated_at": now,
        }
        self.safe_drive_write_service.replace_document(self.profile_path(public_buyer_id), profile)
        self.safe_drive_write_service.append_record(
            self.index_path,
            "buyers",
            {
                "public_buyer_id": public_buyer_id,
                "email": profile["email"],
                "full_name": profile["full_name"],
                "status": "ACTIVE",
                "created_at": now,
                "updated_at": now,
            },
        )
        return profile

    def upsert_profile(self, public_buyer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        profile = self.get_by_id(public_buyer_id)
        if profile is None:
            raise ValueError(f"Public buyer not found: {public_buyer_id}")
        merged = self._deep_merge(dict(profile), updates)
        merged["public_buyer_id"] = public_buyer_id
        merged["email"] = str(merged.get("email", profile.get("email", ""))).strip().lower()
        merged["updated_at"] = datetime.now(UTC).isoformat()
        self.safe_drive_write_service.replace_document(self.profile_path(public_buyer_id), merged)
        self.safe_drive_write_service.update_record(
            self.index_path,
            "buyers",
            matcher=lambda item: item.get("public_buyer_id") == public_buyer_id,
            updater=lambda item: {
                **item,
                "email": merged["email"],
                "full_name": merged.get("full_name", ""),
                "status": merged.get("status", "ACTIVE"),
                "updated_at": merged["updated_at"],
            },
        )
        return merged

    def _deep_merge(self, current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
