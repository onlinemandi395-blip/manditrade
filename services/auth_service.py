from __future__ import annotations


class AuthService:
    def resolve_user(self, role: str) -> dict:
        return {"role": role}
