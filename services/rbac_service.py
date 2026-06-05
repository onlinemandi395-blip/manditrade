from __future__ import annotations


class RBACService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service

    def get_permissions(self, role: str) -> list[str]:
        return list(self.cache_service.get_config("permissions").get("permissions", {}).get(role, []))

    def can_access(self, role: str, route: str) -> bool:
        permissions = self.get_permissions(role)
        return "*" in permissions or route in permissions
