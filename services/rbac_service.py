from __future__ import annotations


class RBACService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service

    def can_access(self, role: str, visible_to: list[str]) -> bool:
        return role in visible_to
