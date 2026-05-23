from __future__ import annotations

from typing import Any


class TokenRotationService:
    def __init__(self, auth_service) -> None:
        self.auth_service = auth_service

    def refresh_runtime_credentials(self, credentials_payload: dict[str, Any]):
        return self.auth_service.refresh_credentials(credentials_payload)

    def build_rotated_payload(self, credentials) -> dict[str, Any]:
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
        }
