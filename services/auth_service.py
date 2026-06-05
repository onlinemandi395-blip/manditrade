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

    def resolve_user(self, email: str) -> dict:
        normalized_email = email.strip().lower()
        user_rows = self.cache_service.get_config("users").get("users", [])
        matched = next(
            (row for row in user_rows if str(row.get("email", "")).strip().lower() == normalized_email),
            None,
        )
        if matched and str(matched.get("status", "ACTIVE")).upper() == "ACTIVE":
            return {
                "email": normalized_email,
                "role": str(matched.get("role", self.get_unknown_user_default_role())),
                "status": "ACTIVE",
                "known_user": True,
            }
        return {
            "email": normalized_email,
            "role": self.get_unknown_user_default_role(),
            "status": "ACTIVE",
            "known_user": False,
        }
