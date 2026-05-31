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
    base_role: str | None = None
    active_context: str | None = None
    manufacturer_code: str | None = None
    session_source: str = "mock"
    subject_id: str | None = None
    granted_scopes: list[str] | None = None
    token_metadata: dict[str, Any] | None = None


class AuthService:
    def __init__(self, oauth_config: dict[str, Any], enable_mock_auth: bool) -> None:
        self.oauth_config = oauth_config["google_oauth"]
        self.enable_mock_auth = enable_mock_auth
        os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

    def build_flow(self, scopes: list[str] | None = None) -> Flow:
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
            scopes=scopes or self.oauth_config["scopes"],
            redirect_uri=self.oauth_config["redirect_uri"],
        )

    def build_authorization_url(self, scopes: list[str] | None = None) -> str | None:
        if not self.oauth_config["client_id"] or not self.oauth_config["client_secret"]:
            return None
        flow = self.build_flow(scopes=scopes)
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return authorization_url

    def create_mock_user(self, email: str, name: str, role: str, manufacturer_code: str | None = None) -> AuthUser:
        if not self.enable_mock_auth:
            raise PermissionError("Mock authentication is disabled.")
        self._validate_role(role)
        return AuthUser(
            email=email,
            name=name,
            role=role,
            base_role=role,
            active_context=role,
            manufacturer_code=manufacturer_code,
            session_source="mock",
        )

    def create_authenticated_user(
        self,
        *,
        profile: dict[str, Any],
        email: str,
        role: str,
        subject_id: str | None = None,
        manufacturer_code: str | None = None,
        granted_scopes: list[str] | None = None,
        token_metadata: dict[str, Any] | None = None,
    ) -> AuthUser:
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise PermissionError("Authenticated Google profile is missing an email address.")
        if not profile.get("verified_email", True):
            raise PermissionError("Authenticated Google email is not verified.")
        resolved_subject = (subject_id or profile.get("id") or "").strip()
        if not resolved_subject:
            raise PermissionError("Authenticated Google profile is missing a subject identifier.")
        self._validate_role(role)
        name = str(profile.get("name") or profile.get("email") or normalized_email).strip()
        if not name:
            raise PermissionError("Authenticated Google profile is missing a display name.")
        return AuthUser(
            email=normalized_email,
            name=name,
            role=role,
            base_role=role,
            active_context=role,
            manufacturer_code=manufacturer_code,
            session_source="google_oauth",
            subject_id=resolved_subject,
            granted_scopes=list(granted_scopes or []),
            token_metadata=dict(token_metadata or {}),
        )

    def _validate_role(self, role: str) -> None:
        if role not in {"admin", "manufacturer", "client", "worker", "platform_admin", "admin_as_manufacturer", "pending_user", "public_buyer"}:
            raise PermissionError(f"Unsupported user role: {role}")

    def serialize_user(self, user: AuthUser) -> dict[str, Any]:
        return asdict(user)

    def deserialize_user(self, payload: dict[str, Any] | None) -> AuthUser | None:
        if not payload:
            return None
        payload = dict(payload)
        payload.setdefault("base_role", payload.get("role"))
        payload.setdefault("active_context", payload.get("active_context") or payload.get("role"))
        return AuthUser(**payload)

    def refresh_credentials(self, credentials_payload: dict[str, Any], scopes: list[str] | None = None) -> Credentials:
        credentials = Credentials.from_authorized_user_info(credentials_payload, scopes or self.oauth_config["scopes"])
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        return credentials

    def fetch_google_profile(self, credentials: Credentials) -> dict[str, Any]:
        service = build("oauth2", "v2", credentials=credentials)
        return service.userinfo().get().execute()
