from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class AccessPortalService:
    def __init__(
        self,
        *,
        governance_root: Path,
        safe_drive_write_service,
        governance_service,
        client_service,
        worker_service,
        public_buyer_service,
        drive_service,
        security_service,
        json_service,
    ) -> None:
        self.governance_root = governance_root
        self.safe_drive_write_service = safe_drive_write_service
        self.governance_service = governance_service
        self.client_service = client_service
        self.worker_service = worker_service
        self.public_buyer_service = public_buyer_service
        self.drive_service = drive_service
        self.security_service = security_service
        self.json_service = json_service

    @property
    def access_requests_path(self) -> Path:
        return self.governance_root / "access_requests.json"

    def ensure_file(self) -> None:
        if not self.access_requests_path.exists():
            self.safe_drive_write_service.replace_document(
                self.access_requests_path,
                {"schema_version": "1.0", "requests": []},
            )

    def list_requests(self, *, role: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        self.ensure_file()
        requests = self.json_service.read_json(self.access_requests_path, {"requests": []}).get("requests", [])
        if role:
            requests = [item for item in requests if item.get("requested_role") == role]
        if status:
            requests = [item for item in requests if item.get("status") == status]
        requests.sort(key=lambda item: item.get("updated_at", item.get("created_at", "")), reverse=True)
        return requests

    def find_latest_request(self, email: str, role: str | None = None) -> dict[str, Any] | None:
        email_key = email.strip().lower()
        for item in self.list_requests(role=role):
            if item.get("email", "").strip().lower() == email_key:
                return item
        return None

    def submit_signup_request(
        self,
        *,
        requested_role: str,
        email: str,
        full_name: str,
        manufacturer_code: str = "",
        manufacturer_name: str = "",
        city: str = "",
        mobile: str = "",
        area: str = "",
        skills: list[str] | None = None,
        preferred_work_type: list[str] | None = None,
        onboarding_secret: str = "",
        invite_token: str = "",
        business_name: str = "",
        note: str = "",
    ) -> dict[str, Any]:
        self.ensure_file()
        email_key = email.strip().lower()
        role_key = requested_role.strip().lower()
        manufacturer_key = manufacturer_code.strip().upper()
        validated = False
        status = "PENDING_ADMIN_REVIEW"
        validation_message = "Request saved for admin review."

        if role_key == "manufacturer" and manufacturer_key:
            manufacturer = self.governance_service.get_manufacturer(manufacturer_key)
            owner_email = (manufacturer or {}).get("owner_email", "").strip().lower()
            secret_match = bool(manufacturer and onboarding_secret.strip() and manufacturer.get("manufacturer_onboarding_secret", "").strip() == onboarding_secret.strip())
            email_match = bool(not owner_email or owner_email == email_key)
            validated = bool(secret_match and email_match)
            if validated:
                status = "READY_FOR_GOOGLE_SIGNIN"
                validation_message = "Manufacturer onboarding packet validated. Continue with Google sign-in."
        elif role_key == "client" and manufacturer_key and invite_token.strip():
            invite = self.client_service.validate_onboarding(manufacturer_key, invite_token.strip(), email_key)
            validated = invite is not None
            if validated:
                status = "READY_FOR_GOOGLE_SIGNIN"
                validation_message = "Client invitation validated. Continue with Google sign-in."
        elif role_key == "worker":
            validated = True
            status = "READY_FOR_GOOGLE_SIGNIN"
            validation_message = "Worker profile request is ready. Continue with Google sign-in."
        elif role_key == "public_buyer":
            validated = True
            status = "READY_FOR_GOOGLE_SIGNIN"
            validation_message = "Public marketplace buyer registration is ready. Continue with Google sign-in."

        record = {
            "request_id": f"ACCESS-{uuid4().hex[:10].upper()}",
            "requested_role": role_key,
            "email": email_key,
            "full_name": full_name.strip(),
            "manufacturer_code": manufacturer_key,
            "manufacturer_name": manufacturer_name.strip(),
            "city": city.strip(),
            "mobile": mobile.strip(),
            "area": area.strip(),
            "skills": [item.strip() for item in (skills or []) if item.strip()],
            "preferred_work_type": [item.strip() for item in (preferred_work_type or []) if item.strip()],
            "business_name": business_name.strip(),
            "invite_token": invite_token.strip(),
            "status": status,
            "validated": validated,
            "validation_message": validation_message,
            "note": note.strip(),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        existing = self.find_latest_request(email_key, role_key)
        if existing:
            record["request_id"] = existing["request_id"]

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload.setdefault("schema_version", "1.0")
            payload.setdefault("requests", [])
            replaced = False
            for index, item in enumerate(payload["requests"]):
                if item.get("request_id") == record["request_id"]:
                    payload["requests"][index] = {**item, **record}
                    replaced = True
                    break
            if not replaced:
                payload["requests"].append(record)
            return payload

        self.safe_drive_write_service.mutate_json(self.access_requests_path, mutator)
        return record

    def resolve_identity(
        self,
        *,
        email: str,
        display_name: str = "",
        preferred_role: str | None = None,
        manufacturer_code: str | None = None,
    ) -> dict[str, Any]:
        email_key = email.strip().lower()
        preferred_role_key = (preferred_role or "").strip().lower()

        if self.security_service.get_admin_email() and email_key == self.security_service.get_admin_email().strip().lower():
            return {"role": "platform_admin", "manufacturer_code": manufacturer_code, "status": "AUTHORIZED"}

        manufacturer = next(
            (item for item in self.governance_service.list_manufacturers() if item.get("owner_email", "").strip().lower() == email_key),
            None,
        )
        if manufacturer:
            return {"role": "manufacturer", "manufacturer_code": manufacturer.get("manufacturer_code"), "status": manufacturer.get("status", "ACTIVE")}

        request = self.find_latest_request(email_key, preferred_role_key or None)
        if request and request.get("status") == "READY_FOR_GOOGLE_SIGNIN":
            return self._activate_request(request, display_name=display_name)

        client_match = self._find_client_membership(email_key)
        if client_match:
            return {"role": "client", "manufacturer_code": client_match["manufacturer_code"], "status": client_match.get("status", "ACTIVE")}

        worker = self.worker_service.get_worker_by_email(email_key)
        if worker:
            return {"role": "worker", "manufacturer_code": None, "status": worker.get("status", "ACTIVE")}

        public_buyer = self.public_buyer_service.get_by_email(email_key)
        if public_buyer:
            return {"role": "public_buyer", "manufacturer_code": None, "status": public_buyer.get("status", "ACTIVE")}

        if request:
            return {
                "role": "pending_user",
                "manufacturer_code": request.get("manufacturer_code") or manufacturer_code,
                "status": request.get("status", "PENDING_ADMIN_REVIEW"),
            }

        if preferred_role_key == "worker":
            self.worker_service.upsert_worker(
                linked_email=email_key,
                name=display_name or email_key,
                mobile="",
                city="",
                area="",
                skills=[],
                preferred_work_type=["Daily Wage"],
                available=True,
                public_profile_opt_in=False,
            )
            return {"role": "worker", "manufacturer_code": None, "status": "SELF_REGISTERED"}

        if preferred_role_key == "public_buyer":
            buyer = self.public_buyer_service.register_or_get(email=email_key, full_name=display_name or email_key)
            return {"role": "public_buyer", "manufacturer_code": None, "status": buyer.get("status", "ACTIVE")}

        return {
            "role": "pending_user",
            "manufacturer_code": manufacturer_code,
            "status": "NO_ACCESS_MAPPING",
        }

    def _activate_request(self, request: dict[str, Any], *, display_name: str = "") -> dict[str, Any]:
        role = request.get("requested_role", "")
        email = request.get("email", "").strip().lower()
        manufacturer_code = request.get("manufacturer_code", "").strip().upper()

        if role == "manufacturer" and manufacturer_code:
            manufacturer = self.governance_service.get_manufacturer(manufacturer_code)
            if manufacturer:
                updates: dict[str, Any] = {}
                if not manufacturer.get("owner_email"):
                    updates["owner_email"] = email
                if manufacturer.get("status") != "ACTIVE":
                    updates["status"] = "ACTIVE"
                if updates:
                    self.governance_service.update_manufacturer(manufacturer_code, updates)
                self._mark_request_status(request["request_id"], "ACTIVE")
                return {"role": "manufacturer", "manufacturer_code": manufacturer_code, "status": "ACTIVE"}

        if role == "client" and manufacturer_code and request.get("invite_token"):
            invite = self.client_service.validate_onboarding(manufacturer_code, request["invite_token"], email)
            if invite:
                profile = {
                    "client_id": invite["client_id"],
                    "manufacturer_id": manufacturer_code,
                    "business_name": request.get("business_name") or invite.get("business_name", ""),
                    "owner_name": request.get("full_name") or display_name or email,
                    "email": email,
                    "city": request.get("city", ""),
                    "credit_limit": 0,
                    "status": "ACTIVE",
                }
                self.client_service.complete_profile(manufacturer_code, profile)
                self._mark_request_status(request["request_id"], "ACTIVE")
                return {"role": "client", "manufacturer_code": manufacturer_code, "status": "ACTIVE"}

        if role == "worker":
            self.worker_service.upsert_worker(
                linked_email=email,
                name=request.get("full_name") or display_name or email,
                mobile=request.get("mobile", ""),
                city=request.get("city", ""),
                area=request.get("area", ""),
                skills=request.get("skills", []),
                preferred_work_type=request.get("preferred_work_type", ["Daily Wage"]),
                available=True,
                public_profile_opt_in=True,
            )
            self._mark_request_status(request["request_id"], "ACTIVE")
            return {"role": "worker", "manufacturer_code": None, "status": "ACTIVE"}

        if role == "public_buyer":
            buyer = self.public_buyer_service.register_or_get(email=email, full_name=request.get("full_name") or display_name or email)
            self._mark_request_status(request["request_id"], "ACTIVE")
            return {"role": "public_buyer", "manufacturer_code": None, "status": buyer.get("status", "ACTIVE")}

        return {"role": "pending_user", "manufacturer_code": manufacturer_code or None, "status": request.get("status", "PENDING_ADMIN_REVIEW")}

    def _find_client_membership(self, email: str) -> dict[str, Any] | None:
        for manufacturer in self.governance_service.list_manufacturers():
            manufacturer_code = manufacturer.get("manufacturer_code", "")
            if not manufacturer_code:
                continue
            profiles = self.client_service.list_client_profiles(manufacturer_code)
            for profile in profiles:
                if profile.get("email", "").strip().lower() == email:
                    return {"manufacturer_code": manufacturer_code, "status": profile.get("status", "ACTIVE")}
            for client in self.client_service.list_clients(manufacturer_code):
                if client.get("email", "").strip().lower() == email:
                    return {"manufacturer_code": manufacturer_code, "status": client.get("status", "INVITED")}
        return None

    def _mark_request_status(self, request_id: str, status: str) -> None:
        self.ensure_file()

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            for item in payload.get("requests", []):
                if item.get("request_id") == request_id:
                    item["status"] = status
                    item["updated_at"] = datetime.now(UTC).isoformat()
                    return payload
            return payload

        self.safe_drive_write_service.mutate_json(self.access_requests_path, mutator)
