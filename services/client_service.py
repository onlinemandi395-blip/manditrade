from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.drive_service import DriveService
from services.encryption_service import EncryptionService
from services.gmail_service import GmailService
from services.json_service import JsonService


class ClientService:
    VALID_STATUSES = {"INVITED", "ACTIVE", "INACTIVE", "BLOCKED"}
    VALID_INVITE_STATUSES = {"PENDING", "SENT", "FAILED", "ACCEPTED"}

    def __init__(
        self,
        drive_service: DriveService,
        gmail_service: GmailService,
        encryption_service: EncryptionService,
        safe_drive_write_service,
        id_allocator_service=None,
        logging_service=None,
    ) -> None:
        self.drive_service = drive_service
        self.gmail_service = gmail_service
        self.encryption_service = encryption_service
        self.safe_drive_write_service = safe_drive_write_service
        self.id_allocator_service = id_allocator_service
        self.logging_service = logging_service
        self.json_service = JsonService()

    def _private_paths(self, manufacturer_code: str) -> dict[str, Path]:
        paths = self.drive_service.get_manufacturer_paths(manufacturer_code)
        return {
            "clients_json": paths.private_zone / "clients.json",
            "profiles_dir": paths.private_zone / "client_profiles",
            "orders_dir": paths.private_zone / "client_orders",
        }

    def _default_clients_doc(self, manufacturer_code: str) -> dict[str, Any]:
        return {"schema_version": "1.0", "manufacturer_code": manufacturer_code, "clients": []}

    def _ensure_clients_doc(self, manufacturer_code: str) -> Path:
        path = self._private_paths(manufacturer_code)["clients_json"]
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, self._default_clients_doc(manufacturer_code), schema_name="clients")
        return path

    def _generate_client_id(self) -> str:
        return self.id_allocator_service.allocate("client") if self.id_allocator_service else f"CLIENT-{datetime.now(UTC).year}-000001"

    def _build_client_record(self, manufacturer_code: str, payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
        existing = existing or {}
        address = payload.get("address", {}) or {}
        delivery_contact = payload.get("delivery_contact", {}) or {}
        now = datetime.now(UTC).isoformat()
        status = str(payload.get("status") or existing.get("status") or "INVITED").strip().upper()
        invite_status = str(payload.get("invite_status") or existing.get("invite_status") or "PENDING").strip().upper()
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid client status: {status}")
        if invite_status not in self.VALID_INVITE_STATUSES:
            raise ValueError(f"Invalid invite status: {invite_status}")
        email = str(payload.get("email") or existing.get("email") or "").strip().lower()
        if not email:
            raise ValueError("Client email is required.")
        business_name = str(payload.get("business_name") or existing.get("business_name") or "").strip()
        if not business_name:
            raise ValueError("Client business name is required.")
        owner_name = str(payload.get("owner_name") or existing.get("owner_name") or "").strip()
        if not owner_name:
            raise ValueError("Client owner name is required.")
        return {
            "client_id": str(payload.get("client_id") or existing.get("client_id") or self._generate_client_id()).strip(),
            "manufacturer_id": manufacturer_code,
            "business_name": business_name,
            "owner_name": owner_name,
            "email": email,
            "mobile": str(payload.get("mobile") or existing.get("mobile") or "").strip(),
            "alternate_mobile": str(payload.get("alternate_mobile") or existing.get("alternate_mobile") or "").strip(),
            "gstin": str(payload.get("gstin") or existing.get("gstin") or "").strip().upper(),
            "pan": str(payload.get("pan") or existing.get("pan") or "").strip().upper(),
            "address": {
                "line1": str(address.get("line1") or existing.get("address", {}).get("line1") or "").strip(),
                "line2": str(address.get("line2") or existing.get("address", {}).get("line2") or "").strip(),
                "city": str(address.get("city") or payload.get("city") or existing.get("address", {}).get("city") or "").strip(),
                "state": str(address.get("state") or existing.get("address", {}).get("state") or "").strip(),
                "pin_code": str(address.get("pin_code") or existing.get("address", {}).get("pin_code") or "").strip(),
                "landmark": str(address.get("landmark") or existing.get("address", {}).get("landmark") or "").strip(),
            },
            "delivery_contact": {
                "name": str(delivery_contact.get("name") or existing.get("delivery_contact", {}).get("name") or owner_name).strip(),
                "mobile": str(delivery_contact.get("mobile") or existing.get("delivery_contact", {}).get("mobile") or "").strip(),
            },
            "delivery_instructions": str(payload.get("delivery_instructions") or existing.get("delivery_instructions") or "").strip(),
            "credit_limit": int(payload.get("credit_limit", existing.get("credit_limit", 0)) or 0),
            "ledger_allowed": bool(payload.get("ledger_allowed", existing.get("ledger_allowed", True))),
            "status": status,
            "invite_status": invite_status,
            "onboarding_token": str(payload.get("onboarding_token") or existing.get("onboarding_token") or "").strip(),
            "created_at": existing.get("created_at") or payload.get("created_at") or now,
            "updated_at": now,
        }

    def list_clients(self, manufacturer_code: str) -> list[dict[str, Any]]:
        path = self._ensure_clients_doc(manufacturer_code)
        payload = self.json_service.read_json(path, self._default_clients_doc(manufacturer_code))
        return payload.get("clients", [])

    def get_client(self, manufacturer_code: str, client_id: str) -> dict[str, Any] | None:
        return next((item for item in self.list_clients(manufacturer_code) if item.get("client_id") == client_id), None)

    def get_client_by_email(self, manufacturer_code: str, email: str) -> dict[str, Any] | None:
        email_key = email.strip().lower()
        return next((item for item in self.list_clients(manufacturer_code) if item.get("email", "").strip().lower() == email_key), None)

    def create_client(self, manufacturer_code: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._ensure_clients_doc(manufacturer_code)
        if self.get_client_by_email(manufacturer_code, str(payload.get("email") or "")):
            raise ValueError("Client email already exists for this manufacturer.")
        record = self._build_client_record(manufacturer_code, payload)
        self.safe_drive_write_service.append_record(path, "clients", record, schema_name="clients")
        return record

    def update_client(self, manufacturer_code: str, client_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_client(manufacturer_code, client_id)
        if existing is None:
            raise ValueError(f"Client not found: {client_id}")
        updated = self._build_client_record(manufacturer_code, {**existing, **updates, "client_id": client_id}, existing)
        path = self._ensure_clients_doc(manufacturer_code)
        self.safe_drive_write_service.update_record(
            path,
            "clients",
            matcher=lambda client: client.get("client_id") == client_id,
            updater=lambda _client: updated,
            schema_name="clients",
        )
        profile = self.get_client_profile_by_email(manufacturer_code, existing.get("email", ""))
        if profile:
            profile_payload = {"schema_version": "1.0", **profile, **updated}
            profiles_dir = self._private_paths(manufacturer_code)["profiles_dir"]
            profiles_dir.mkdir(parents=True, exist_ok=True)
            self.safe_drive_write_service.replace_document(profiles_dir / f"{client_id}.json", profile_payload, schema_name="profile")
        return updated

    def deactivate_client(self, manufacturer_code: str, client_id: str) -> dict[str, Any]:
        return self.update_client(manufacturer_code, client_id, {"status": "INACTIVE"})

    def create_invite(self, manufacturer_code: str, email: str, business_name: str, owner_name: str = "") -> dict[str, Any]:
        existing = self.get_client_by_email(manufacturer_code, email)
        onboarding_token = self.encryption_service.encrypt(f"{manufacturer_code}|{email.strip().lower()}|{(existing or {}).get('client_id') or self._generate_client_id()}")
        payload = {
            "email": email,
            "business_name": business_name,
            "owner_name": owner_name or business_name,
            "status": "INVITED",
            "invite_status": "PENDING",
            "onboarding_token": onboarding_token,
        }
        if existing:
            invite = self.update_client(manufacturer_code, existing["client_id"], payload)
        else:
            invite = self.create_client(manufacturer_code, payload)
        return invite

    def send_invitation(self, manufacturer_code: str, client_id: str, manufacturer_name: str, login_link: str) -> dict[str, Any]:
        client = self.get_client(manufacturer_code, client_id)
        if client is None:
            raise ValueError(f"Client not found: {client_id}")
        body = (
            f"{manufacturer_name} invited you to join MandiTrade.\n"
            f"Business: {client['business_name']}\n"
            f"Sign in with Google here: {login_link}\n"
            "Use the same invited email to activate your private client profile."
        )
        try:
            self.gmail_service.enqueue_message(
                to_email=client["email"],
                subject=f"MandiTrade invite from {manufacturer_name}",
                body=body,
                notification_type="client_invited",
            )
        except Exception as exc:  # noqa: BLE001
            if self.logging_service:
                self.logging_service.log_error("client_invites", str(exc), {"manufacturer_code": manufacturer_code, "client_id": client_id})
            return self.update_client(manufacturer_code, client_id, {"invite_status": "FAILED"})
        return self.update_client(manufacturer_code, client_id, {"invite_status": "SENT", "status": "INVITED"})

    def validate_onboarding(self, manufacturer_code: str, onboarding_token: str, email: str) -> dict[str, Any] | None:
        email_key = email.strip().lower()
        return next(
            (
                client
                for client in self.list_clients(manufacturer_code)
                if client.get("onboarding_token") == onboarding_token and client.get("email", "").strip().lower() == email_key
            ),
            None,
        )

    def complete_profile(self, manufacturer_code: str, profile: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_client(profile.get("manufacturer_id", manufacturer_code), profile.get("client_id", ""))
        if existing is None and profile.get("email"):
            existing = self.get_client_by_email(manufacturer_code, str(profile.get("email")))
        merged = self._build_client_record(manufacturer_code, {**(existing or {}), **profile, "status": "ACTIVE", "invite_status": "ACCEPTED"}, existing)
        paths = self._private_paths(manufacturer_code)
        profiles_dir = paths["profiles_dir"]
        profiles_dir.mkdir(parents=True, exist_ok=True)
        self.safe_drive_write_service.replace_document(profiles_dir / f"{merged['client_id']}.json", {"schema_version": "1.0", **merged}, schema_name="profile")
        if existing:
            self.update_client(manufacturer_code, existing["client_id"], merged)
        else:
            self.create_client(manufacturer_code, merged)
        return merged

    def get_client_profile_by_email(self, manufacturer_code: str, email: str) -> dict[str, Any] | None:
        email_key = email.strip().lower()
        return next((item for item in self.list_client_profiles(manufacturer_code) if item.get("email", "").strip().lower() == email_key), None)

    def upsert_client_profile(self, manufacturer_code: str, email: str, updates: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_client_profile_by_email(manufacturer_code, email)
        invite = self.get_client_by_email(manufacturer_code, email)
        if existing is None and invite is None:
            raise ValueError("No active client invitation or profile found for this account.")
        base_profile = dict(existing or invite or {})
        merged = {**base_profile, **updates, "client_id": base_profile.get("client_id", ""), "manufacturer_id": manufacturer_code, "email": email.strip().lower()}
        return self.complete_profile(manufacturer_code, merged)

    def list_client_profiles(self, manufacturer_code: str) -> list[dict[str, Any]]:
        profiles_dir = self._private_paths(manufacturer_code)["profiles_dir"]
        if not profiles_dir.exists():
            return []
        return [self.json_service.read_json(path, {}) for path in sorted(profiles_dir.glob("*.json"))]

    def summarize_clients(self, manufacturer_code: str) -> dict[str, Any]:
        clients = self.list_clients(manufacturer_code)
        status_counts: dict[str, int] = {}
        invite_counts: dict[str, int] = {}
        for client in clients:
            status = str(client.get("status") or "UNKNOWN").strip().upper()
            invite_status = str(client.get("invite_status") or "UNKNOWN").strip().upper()
            status_counts[status] = status_counts.get(status, 0) + 1
            invite_counts[invite_status] = invite_counts.get(invite_status, 0) + 1
        return {
            "manufacturer_code": manufacturer_code,
            "total_clients": len(clients),
            "active_clients": status_counts.get("ACTIVE", 0),
            "invited_clients": status_counts.get("INVITED", 0),
            "inactive_clients": status_counts.get("INACTIVE", 0),
            "blocked_clients": status_counts.get("BLOCKED", 0),
            "status_counts": status_counts,
            "invite_status_counts": invite_counts,
        }

    def summarize_credit(self, manufacturer_code: str, client_id: str, ledger_service) -> dict[str, Any]:
        client = self.get_client(manufacturer_code, client_id)
        if client is None:
            raise ValueError(f"Client not found: {client_id}")
        outstanding = 0.0
        for ledger in ledger_service.list_ledgers(manufacturer_code):
            if ledger.get("party_b") != client_id:
                continue
            for entry in ledger.get("entries", []):
                outstanding += float(entry.get("balance_due", 0) or 0)
        credit_limit = float(client.get("credit_limit", 0) or 0)
        available_credit = round(max(credit_limit - outstanding, 0), 2)
        if credit_limit <= 0:
            status = "OK"
        elif outstanding > credit_limit:
            status = "BLOCKED"
        elif outstanding >= credit_limit * 0.8:
            status = "NEAR_LIMIT"
        else:
            status = "OK"
        return {
            "credit_limit": round(credit_limit, 2),
            "current_outstanding": round(outstanding, 2),
            "available_credit": available_credit,
            "credit_status": status,
        }

    def can_place_credit_order(
        self,
        manufacturer_code: str,
        client_id: str,
        *,
        proposed_order_amount: float,
        ledger_service,
        allow_override: bool = False,
    ) -> tuple[bool, dict[str, Any]]:
        summary = self.summarize_credit(manufacturer_code, client_id, ledger_service)
        limit = float(summary["credit_limit"])
        if allow_override or limit <= 0:
            return True, summary
        allowed = (float(summary["current_outstanding"]) + float(proposed_order_amount or 0)) <= limit
        return allowed, summary
