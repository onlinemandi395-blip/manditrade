from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import logging


LOGGER = logging.getLogger(__name__)


class UserProfileService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.admin_drive_service = data_service.admin_drive_service

    def _normalize_email(self, email: str) -> str:
        return str(email or "").strip().lower()

    def _profile_logical_path(self, email: str) -> str:
        return f"{self._workspace_logical_path(email)}/profile.json"

    def _orders_logical_path(self, email: str) -> str:
        return f"{self._workspace_logical_path(email)}/orders.json"

    def _workspace_name(self, email: str) -> str:
        normalized_email = self._normalize_email(email)
        return normalized_email.replace("@", "_at_").replace(".", "_")

    def _workspace_logical_path(self, email: str) -> str:
        return f"01_identity/profiles/{self._workspace_name(email)}"

    def _default_business_details(self) -> dict:
        return {
            "schema_version": 1,
            "business_name": "",
            "upi_id": "",
            "gst_number": "",
            "invoice_name": "",
            "invoice_address": "",
            "invoice_phone": "",
            "bank_account_name": "",
            "bank_account_number": "",
            "bank_ifsc": "",
            "other_details": "",
            "profile_completed": False,
        }

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
                "workspace_folder": self._workspace_logical_path(normalized_email),
                "addresses": [],
                "details": self._default_business_details(),
                "created_at": now,
                "updated_at": now,
            },
        }

    def _default_orders_payload(self, email: str) -> dict:
        return {
            "schema_version": 1,
            "user_orders": {
                "email": self._normalize_email(email),
                "orders": [],
            },
        }

    def ensure_user_workspace(self, *, email: str, role: str, display_name: str, mobile: str = "") -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise ValueError("User email is required.")
        resolver = self.admin_drive_service.get_path_resolver()
        folder_result = resolver.ensure_folder_path(self._workspace_logical_path(normalized_email))
        try:
            self.admin_drive_service.google_drive_service.ensure_user_permission(
                resolver.service,
                folder_result["folder_id"],
                normalized_email,
                role="writer",
            )
        except Exception as exc:
            LOGGER.warning(
                "Skipping Drive permission assignment for %s on folder %s: %s",
                normalized_email,
                folder_result.get("folder_id", ""),
                exc,
            )
        resolver.create_or_update_json_file(
            self._profile_logical_path(normalized_email),
            (
                {"schema_version": 1, "user_profile": self.get_profile(normalized_email)}
                if self.get_profile(normalized_email)
                else self._default_profile(
                    email=normalized_email,
                    role=role,
                    display_name=display_name,
                    mobile=mobile,
                )
            ),
        )
        resolver.create_or_update_json_file(
            self._orders_logical_path(normalized_email),
            self._read_user_orders_payload(normalized_email) or self._default_orders_payload(normalized_email),
        )
        return folder_result

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
        profile["workspace_folder"] = self._workspace_logical_path(normalized_email)
        profile.setdefault("addresses", [])
        details = dict(profile.get("details", {}) or {})
        normalized_details = self._default_business_details()
        normalized_details.update(details)
        profile["details"] = normalized_details
        return profile

    def _read_user_orders_payload(self, email: str) -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            return {}
        try:
            return self.admin_drive_service.read_json(self._orders_logical_path(normalized_email))
        except FileNotFoundError:
            return {}

    def get_or_create_profile(self, *, email: str, role: str, display_name: str, mobile: str = "") -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise ValueError("User email is required.")
        existing = self.get_profile(normalized_email)
        if existing:
            existing.setdefault("addresses", [])
            existing["details"] = dict(existing.get("details", {}) or {})
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
        self.ensure_user_workspace(
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
        next_profile["workspace_folder"] = self._workspace_logical_path(normalized_target)
        next_profile["addresses"] = list(next_profile.get("addresses", []) or [])
        normalized_details = self._default_business_details()
        normalized_details.update(dict(next_profile.get("details", {}) or {}))
        next_profile["details"] = normalized_details
        next_profile["updated_at"] = datetime.now(UTC).isoformat()
        if not current:
            self.ensure_user_workspace(
                email=normalized_target,
                role=next_profile.get("role", "public_buyer"),
                display_name=next_profile.get("display_name", normalized_target.split("@")[0]),
                mobile=next_profile.get("mobile", ""),
            )
        self.admin_drive_service.write_json(
            self._profile_logical_path(normalized_target),
            {"schema_version": 1, "user_profile": next_profile},
        )
        return next_profile

    def save_owner_business_details(
        self,
        *,
        actor_email: str,
        actor_role: str,
        target_email: str,
        role: str,
        display_name: str,
        mobile: str,
        business_details: dict,
    ) -> dict:
        current = self.get_or_create_profile(
            email=target_email,
            role=role,
            display_name=display_name,
            mobile=mobile,
        )
        next_profile = dict(current)
        next_profile["display_name"] = str(display_name or current.get("display_name", "")).strip()
        next_profile["mobile"] = str(mobile or current.get("mobile", "")).strip()
        merged_details = self._default_business_details()
        merged_details.update(dict(current.get("details", {}) or {}))
        merged_details.update(dict(business_details or {}))
        required_fields = ("business_name", "upi_id", "gst_number", "invoice_name")
        merged_details["profile_completed"] = all(str(merged_details.get(field, "")).strip() for field in required_fields)
        next_profile["details"] = merged_details
        return self.save_profile(
            actor_email=actor_email,
            actor_role=actor_role,
            target_email=target_email,
            updates=next_profile,
        )

    def sync_order_record(self, *, order: dict) -> None:
        order_id = str(order.get("order_id", "")).strip()
        if not order_id:
            return
        related_emails = {
            self._normalize_email(order.get("buyer_email", "")),
            self._normalize_email(order.get("requester_email", "")),
            self._normalize_email(order.get("owner_email", "")),
            self._normalize_email(order.get("preferred_delivery_partner_email", "")),
            self._normalize_email(((order.get("buyer") or {}).get("email", ""))),
            self._normalize_email(((order.get("requester") or {}).get("email", ""))),
        }
        for email in sorted(email for email in related_emails if email):
            payload = self._read_user_orders_payload(email) or self._default_orders_payload(email)
            user_orders = dict(payload.get("user_orders", {}) or {})
            rows = list(user_orders.get("orders", []) or [])
            existing = next((row for row in rows if str(row.get("order_id", "")).strip() == order_id), None)
            snapshot = deepcopy(order)
            if existing:
                existing.clear()
                existing.update(snapshot)
            else:
                rows.append(snapshot)
            user_orders["email"] = email
            user_orders["orders"] = rows
            payload["user_orders"] = user_orders
            profile = self.get_profile(email)
            if not profile:
                self.ensure_user_workspace(
                    email=email,
                    role=profile.get("role", "public_buyer"),
                    display_name=profile.get("display_name", email.split("@")[0]),
                    mobile=profile.get("mobile", ""),
                )
            self.admin_drive_service.write_json(self._orders_logical_path(email), payload)
