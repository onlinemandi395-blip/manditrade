from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.drive_service import DriveService
from services.encryption_service import EncryptionService
from services.gmail_service import GmailService
from services.json_service import JsonService


class ClientService:
    def __init__(
        self,
        drive_service: DriveService,
        gmail_service: GmailService,
        encryption_service: EncryptionService,
        safe_drive_write_service,
        id_allocator_service=None,
    ) -> None:
        self.drive_service = drive_service
        self.gmail_service = gmail_service
        self.encryption_service = encryption_service
        self.safe_drive_write_service = safe_drive_write_service
        self.id_allocator_service = id_allocator_service
        self.json_service = JsonService()

    def _private_paths(self, manufacturer_code: str) -> dict[str, Path]:
        paths = self.drive_service.get_manufacturer_paths(manufacturer_code)
        return {
            "clients_json": paths.private_zone / "clients.json",
            "profiles_dir": paths.private_zone / "client_profiles",
            "orders_dir": paths.private_zone / "client_orders",
        }

    def create_invite(self, manufacturer_code: str, email: str, business_name: str) -> dict[str, Any]:
        client_id = self.id_allocator_service.allocate("client") if self.id_allocator_service else f"CLIENT{uuid4().hex[:6].upper()}"
        onboarding_token = self.encryption_service.encrypt(f"{manufacturer_code}|{email}|{client_id}")
        invite = {
            "client_id": client_id,
            "manufacturer_id": manufacturer_code,
            "business_name": business_name,
            "email": email,
            "onboarding_token": onboarding_token,
            "status": "INVITED",
            "created_at": datetime.now(UTC).isoformat(),
        }
        paths = self._private_paths(manufacturer_code)
        if not paths["clients_json"].exists():
            self.safe_drive_write_service.replace_document(
                paths["clients_json"],
                {"schema_version": "1.0", "manufacturer_code": manufacturer_code, "clients": []},
                schema_name="clients",
            )
        self.safe_drive_write_service.append_record(paths["clients_json"], "clients", invite, schema_name="clients")
        return invite

    def send_invitation(self, invite: dict[str, Any]) -> None:
        body = (
            f"You have been invited to MandiTrade by manufacturer {invite['manufacturer_id']}.\n"
            f"Use onboarding token: {invite['onboarding_token']}\n"
            "Complete your Google sign-in and profile setup in the app."
        )
        self.gmail_service.enqueue_message(
            to_email=invite["email"],
            subject="MandiTrade Client Invitation",
            body=body,
            notification_type="client_invited",
        )

    def validate_onboarding(self, manufacturer_code: str, onboarding_token: str, email: str) -> dict[str, Any] | None:
        paths = self._private_paths(manufacturer_code)
        payload = self.json_service.read_json(paths["clients_json"], {"clients": []})
        return next(
            (
                client
                for client in payload.get("clients", [])
                if client.get("onboarding_token") == onboarding_token and client.get("email", "").lower() == email.lower()
            ),
            None,
        )

    def complete_profile(self, manufacturer_code: str, profile: dict[str, Any]) -> dict[str, Any]:
        paths = self._private_paths(manufacturer_code)
        profiles_dir = paths["profiles_dir"]
        profiles_dir.mkdir(parents=True, exist_ok=True)
        profile.setdefault("schema_version", "1.0")
        profile["status"] = "ACTIVE"
        profile["updated_at"] = datetime.now(UTC).isoformat()
        self.safe_drive_write_service.replace_document(
            profiles_dir / f"{profile['client_id']}.json",
            profile,
            schema_name="profile",
        )
        self.safe_drive_write_service.update_record(
            paths["clients_json"],
            "clients",
            matcher=lambda client: client.get("client_id") == profile["client_id"] or client.get("email", "").strip().lower() == profile.get("email", "").strip().lower(),
            updater=lambda client: {
                **client,
                "client_id": profile["client_id"],
                "status": "ACTIVE",
                "business_name": profile["business_name"],
                "owner_name": profile["owner_name"],
            },
            schema_name="clients",
        )
        return profile

    def get_client_profile_by_email(self, manufacturer_code: str, email: str) -> dict[str, Any] | None:
        email_key = email.strip().lower()
        return next(
            (
                item
                for item in self.list_client_profiles(manufacturer_code)
                if item.get("email", "").strip().lower() == email_key
            ),
            None,
        )

    def upsert_client_profile(self, manufacturer_code: str, email: str, updates: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_client_profile_by_email(manufacturer_code, email)
        invite = next(
            (
                item
                for item in self.list_clients(manufacturer_code)
                if item.get("email", "").strip().lower() == email.strip().lower()
            ),
            None,
        )
        if existing is None and invite is None:
            raise ValueError("No active client invitation or profile found for this account.")
        base_profile = dict(existing or {})
        if not base_profile:
            base_profile = {
                "client_id": invite.get("client_id", ""),
                "manufacturer_id": manufacturer_code,
                "business_name": invite.get("business_name", ""),
                "owner_name": "",
                "email": email.strip().lower(),
                "status": "ACTIVE",
            }
        merged = self._deep_merge(base_profile, updates)
        merged["client_id"] = merged.get("client_id") or invite.get("client_id", "")
        merged["manufacturer_id"] = manufacturer_code
        merged["email"] = email.strip().lower()
        if not merged.get("client_id"):
            raise ValueError("Client profile is missing a client_id.")
        return self.complete_profile(manufacturer_code, merged)

    def list_clients(self, manufacturer_code: str) -> list[dict[str, Any]]:
        paths = self._private_paths(manufacturer_code)
        return self.json_service.read_json(paths["clients_json"], {"clients": []}).get("clients", [])

    def list_client_profiles(self, manufacturer_code: str) -> list[dict[str, Any]]:
        paths = self._private_paths(manufacturer_code)
        profiles_dir = paths["profiles_dir"]
        if not profiles_dir.exists():
            return []
        return [self.json_service.read_json(path, {}) for path in sorted(profiles_dir.glob("*.json"))]

    def _deep_merge(self, current: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = dict(current)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
