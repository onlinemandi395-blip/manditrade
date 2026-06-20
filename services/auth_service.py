from __future__ import annotations

import streamlit as st


def get_bootstrap_primary_admin() -> dict:
    platform_section = dict(st.secrets.get("platform", {})) if "platform" in st.secrets else {}
    admin_section = dict(st.secrets.get("admin", {})) if "admin" in st.secrets else {}
    email = str(
        platform_section.get("primary_admin_email", "")
        or admin_section.get("email", "")
        or admin_section.get("admin_email", "")
    ).strip().lower()
    name = str(
        platform_section.get("primary_admin_name", "")
        or admin_section.get("name", "")
        or "Primary Admin"
    ).strip()
    return {
        "email": email,
        "role": "platform_admin",
        "status": "ACTIVE",
        "display_name": name,
    }


def is_bootstrap_admin(user_email: str) -> bool:
    normalized_email = str(user_email).strip().lower()
    primary_admin = get_bootstrap_primary_admin()
    return bool(primary_admin.get("email")) and normalized_email == primary_admin["email"]


class AuthService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service

    def get_auth_config(self) -> dict:
        return self.cache_service.get_config("auth").get("authentication", {})

    def get_enabled_providers(self) -> list[dict]:
        providers = self.get_auth_config().get("providers", [])
        return [provider for provider in providers if provider.get("enabled", False)]

    def get_unknown_user_default_role(self) -> str:
        return str(self.get_auth_config().get("unknown_user_default_role", "public_buyer"))

    def get_registered_users(self) -> list[dict]:
        return list(self.cache_service.get_config("users").get("users", []))

    def get_primary_admin(self) -> dict:
        return get_bootstrap_primary_admin()

    def resolve_user(self, email: str) -> dict:
        normalized_email = email.strip().lower()
        primary_admin = self.get_primary_admin()
        if primary_admin.get("email") and normalized_email == primary_admin["email"]:
            return {
                "email": normalized_email,
                "role": "platform_admin",
                "status": "ACTIVE",
                "display_name": primary_admin.get("display_name", "Primary Admin"),
                "known_user": True,
                "is_primary_admin": True,
                "user_found": True,
                "source": "primary_admin",
            }
        user_rows = self.get_registered_users()
        matched = next(
            (row for row in user_rows if str(row.get("email", "")).strip().lower() == normalized_email),
            None,
        )
        if matched and str(matched.get("status", "ACTIVE")).upper() == "ACTIVE":
            return {
                **matched,
                "email": normalized_email,
                "role": str(matched.get("role", self.get_unknown_user_default_role())),
                "status": "ACTIVE",
                "display_name": str(matched.get("display_name", normalized_email.split("@")[0] if normalized_email else "")),
                "known_user": True,
                "is_primary_admin": False,
                "user_found": True,
                "source": "users.json",
            }
        return {
            "email": normalized_email,
            "role": self.get_unknown_user_default_role(),
            "status": "ACTIVE",
            "display_name": normalized_email.split("@")[0] if normalized_email else "",
            "known_user": False,
            "is_primary_admin": False,
            "user_found": False,
            "source": "unknown_user_default",
        }

    def login(self, email: str, provider_id: str) -> dict:
        user = self.resolve_user(email)
        return {
            **user,
            "provider_id": provider_id,
        }
