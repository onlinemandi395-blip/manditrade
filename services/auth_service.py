from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


@dataclass(slots=True)
class AuthUser:
    email: str
    name: str
    role: str
    manufacturer_code: str | None = None


class AuthService:
    def __init__(self, oauth_config: dict[str, Any], enable_mock_auth: bool) -> None:
        self.oauth_config = oauth_config["google_oauth"]
        self.enable_mock_auth = enable_mock_auth
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    def build_flow(self) -> Flow:
        config = {
            "web": {
                "client_id": self.oauth_config["client_id"],
                "project_id": self.oauth_config["project_id"],
                "auth_uri": self.oauth_config["auth_uri"],
                "token_uri": self.oauth_config["token_uri"],
                "client_secret": self.oauth_config["client_secret"],
                "redirect_uris": [self.oauth_config["redirect_uri"]],
            }
        }
        return Flow.from_client_config(
            config,
            scopes=self.oauth_config["scopes"],
            redirect_uri=self.oauth_config["redirect_uri"],
        )

    def build_authorization_url(self) -> str | None:
        if not self.oauth_config["client_id"] or not self.oauth_config["client_secret"]:
            return None
        flow = self.build_flow()
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return authorization_url

    def create_mock_user(self, email: str, name: str, role: str, manufacturer_code: str | None = None) -> AuthUser:
        if not self.enable_mock_auth:
            raise PermissionError("Mock authentication is disabled.")
        return AuthUser(email=email, name=name, role=role, manufacturer_code=manufacturer_code)

    def serialize_user(self, user: AuthUser) -> dict[str, Any]:
        return asdict(user)

    def deserialize_user(self, payload: dict[str, Any] | None) -> AuthUser | None:
        if not payload:
            return None
        return AuthUser(**payload)

    def refresh_credentials(self, credentials_payload: dict[str, Any]) -> Credentials:
        credentials = Credentials.from_authorized_user_info(credentials_payload, self.oauth_config["scopes"])
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        return credentials

    def fetch_google_profile(self, credentials: Credentials) -> dict[str, Any]:
        service = build("oauth2", "v2", credentials=credentials)
        return service.userinfo().get().execute()
