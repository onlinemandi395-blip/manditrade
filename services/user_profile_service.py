from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime


class UserProfileService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.admin_drive_service = data_service.admin_drive_service

    def _normalize_email(self, email: str) -> str:
        return str(email or "").strip().lower()

    def _profile_logical_path(self, email: str) -> str:
        normalized_email = self._normalize_email(email)
        safe_name = normalized_email.replace("@", "_at_").replace(".", "_")
        return f"01_identity/profiles/{safe_name}.json"

    def _default_profile(self, *, email: str, role: str, display_name: str, mobile: str = "") -> dict:
        normalized_email = self._normalize_email(email)
        now = datetime.now(UTC).isoformat()
        return {
            "schema_version": 1,
            "user_profile": {
                "email": normalized_email,
                "role": str(role or "public_buyer").strip() or "public_buyer",
                "display_name": str(display_name or normalized_email.split("@")[0]).strip(),
                "mobile": str(mobile or "").strip(),
                "addresses": [],
                "details": {},
                "created_at": now,
                "updated_at": now,
            },
        }

    def get_profile(self, email: str) -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            return {}
        try:
            payload = self.admin_drive_service.read_json(self._profile_logical_path(normalized_email))
        except FileNotFoundError:
            return {}
        profile = dict(payload.get("user_profile", payload) or {})
        profile["email"] = normalized_email
        profile.setdefault("addresses", [])
        profile.setdefault("details", {})
        return profile

    def get_or_create_profile(self, *, email: str, role: str, display_name: str, mobile: str = "") -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise ValueError("User email is required.")
        existing = self.get_profile(normalized_email)
        if existing:
            existing.setdefault("addresses", [])
            existing.setdefault("details", {})
            changed = False
            if str(display_name or "").strip() and str(existing.get("display_name", "")).strip() != str(display_name).strip():
                existing["display_name"] = str(display_name).strip()
                changed = True
            if mobile is not None and str(existing.get("mobile", "")).strip() != str(mobile or "").strip():
                existing["mobile"] = str(mobile or "").strip()
                changed = True
            expected_role = str(role or "public_buyer").strip() or "public_buyer"
            if str(existing.get("role", "")).strip() != expected_role:
                existing["role"] = expected_role
                changed = True
            if changed:
                self.save_profile(
                    actor_email=normalized_email,
                    actor_role=existing.get("role", expected_role),
                    target_email=normalized_email,
                    updates=existing,
                )
                existing = self.get_profile(normalized_email)
            return existing
        payload = self._default_profile(
            email=normalized_email,
            role=role,
            display_name=display_name,
            mobile=mobile,
        )
        self.admin_drive_service.write_json(self._profile_logical_path(normalized_email), payload)
        return dict(payload.get("user_profile", {}) or {})

    def _can_edit(self, *, actor_email: str, actor_role: str, target_email: str) -> bool:
        normalized_actor = self._normalize_email(actor_email)
        normalized_target = self._normalize_email(target_email)
        normalized_role = str(actor_role or "").strip().lower()
        return bool(normalized_actor and normalized_target) and (
            normalized_actor == normalized_target or normalized_role == "platform_admin"
        )

    def save_profile(
        self,
        *,
        actor_email: str,
        actor_role: str,
        target_email: str,
        updates: dict,
    ) -> dict:
        normalized_target = self._normalize_email(target_email)
        if not self._can_edit(actor_email=actor_email, actor_role=actor_role, target_email=normalized_target):
            raise PermissionError("Only the user or a platform admin can update this profile.")
        current = self.get_profile(normalized_target)
        if not current:
            current = dict(
                self._default_profile(
                    email=normalized_target,
                    role=str(updates.get("role", "public_buyer")),
                    display_name=str(updates.get("display_name", normalized_target.split("@")[0])),
                    mobile=str(updates.get("mobile", "")),
                ).get("user_profile", {})
            )
        next_profile = deepcopy(current)
        next_profile.update(dict(updates or {}))
        next_profile["email"] = normalized_target
        next_profile["addresses"] = list(next_profile.get("addresses", []) or [])
        next_profile["details"] = dict(next_profile.get("details", {}) or {})
        next_profile["updated_at"] = datetime.now(UTC).isoformat()
        self.admin_drive_service.write_json(
            self._profile_logical_path(normalized_target),
            {"schema_version": 1, "user_profile": next_profile},
        )
        return next_profile
