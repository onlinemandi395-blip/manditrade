from __future__ import annotations


class RBACService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service

    def get_permissions(self, role: str) -> list[str]:
        permissions = self.cache_service.get_config("permissions").get("permissions", {})
        if role in permissions:
            return list(permissions.get(role, []))
        return list(permissions.get("public_buyer", []))

    def can_access(self, role: str, route: str) -> bool:
        permissions = self.get_permissions(role)
        return "*" in permissions or route in permissions
