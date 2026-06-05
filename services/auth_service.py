from __future__ import annotations


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

    def resolve_user(self, email: str) -> dict:
        normalized_email = email.strip().lower()
        user_rows = self.get_registered_users()
        matched = next(
            (row for row in user_rows if str(row.get("email", "")).strip().lower() == normalized_email),
            None,
        )
        if matched and str(matched.get("status", "ACTIVE")).upper() == "ACTIVE":
            return {
                "email": normalized_email,
                "role": str(matched.get("role", self.get_unknown_user_default_role())),
                "status": "ACTIVE",
                "display_name": str(matched.get("display_name", normalized_email.split("@")[0] if normalized_email else "")),
                "known_user": True,
            }
        return {
            "email": normalized_email,
            "role": self.get_unknown_user_default_role(),
            "status": "ACTIVE",
            "display_name": normalized_email.split("@")[0] if normalized_email else "",
            "known_user": False,
        }

    def login(self, email: str, provider_id: str) -> dict:
        user = self.resolve_user(email)
        return {
            **user,
            "provider_id": provider_id,
        }
