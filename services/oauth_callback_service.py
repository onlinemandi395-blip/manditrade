from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import streamlit as st

from services.auth_service import AuthService
from services.security_service import SecurityService


class OAuthCallbackService:
    LOGIN = "login_oauth"
    MANUFACTURER_DRIVE = "manufacturer_drive_connect"
    MANUFACTURER_GMAIL = "manufacturer_gmail_connect"
    ADMIN_TOKEN = "admin_token_provision"

    FLOW_SCOPES = {
        LOGIN: [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        MANUFACTURER_DRIVE: ["https://www.googleapis.com/auth/drive.file"],
        MANUFACTURER_GMAIL: ["https://www.googleapis.com/auth/gmail.send"],
        ADMIN_TOKEN: None,
    }

    def __init__(
        self,
        auth_service: AuthService,
        security_service: SecurityService,
        state_store_path: Path | None = None,
        runtime_reports_root: Path | None = None,
        runtime_environment: str = "local",
    ) -> None:
        self.auth_service = auth_service
        self.security_service = security_service
        self.state_store_path = state_store_path
        self.runtime_reports_root = runtime_reports_root
        self.runtime_environment = runtime_environment

    def _read_state_store(self) -> dict[str, Any]:
        if not self.state_store_path or not self.state_store_path.exists():
            return {"states": []}
        try:
            return json.loads(self.state_store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"states": []}

    def _write_state_store(self, payload: dict[str, Any]) -> None:
        if not self.state_store_path:
            return
        self.state_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def issue_state_token(self) -> str:
        return secrets.token_urlsafe(24)

    def _store_pending_state(self, token: str, *, flow_type: str, code_verifier: str | None = None, role_context: str = "", manufacturer_id: str = "", scopes: list[str] | None = None) -> None:
        payload = self._read_state_store()
        states = payload.setdefault("states", [])
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        states[:] = [
            item
            for item in states
            if item.get("token") and datetime.fromisoformat(item.get("created_at", datetime.now(UTC).isoformat())) >= cutoff
        ]
        states.append(
            {
                "token": token,
                "flow_type": flow_type,
                "role_context": role_context,
                "manufacturer_id": manufacturer_id,
                "scopes": list(scopes or []),
                "code_verifier": code_verifier or "",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        self._write_state_store(payload)

    def _lookup_pending_state(self, token: str) -> dict[str, Any] | None:
        payload = self._read_state_store()
        states = payload.setdefault("states", [])
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        for item in states:
            created_at_raw = item.get("created_at", datetime.now(UTC).isoformat())
            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                created_at = datetime.now(UTC)
            if created_at < cutoff:
                continue
            if item.get("token") == token:
                return item
        return None

    def _consume_pending_state(self, token: str) -> dict[str, Any] | None:
        payload = self._read_state_store()
        states = payload.setdefault("states", [])
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        matched: dict[str, Any] | None = None
        remaining = []
        for item in states:
            created_at_raw = item.get("created_at", datetime.now(UTC).isoformat())
            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                created_at = datetime.now(UTC)
            if created_at < cutoff:
                continue
            if item.get("token") == token and matched is None:
                matched = item
                continue
            remaining.append(item)
        payload["states"] = remaining
        self._write_state_store(payload)
        return matched

    def build_authorization_url(
        self,
        *,
        flow_type: str = LOGIN,
        role_context: str = "",
        manufacturer_id: str = "",
        scopes: list[str] | None = None,
    ) -> str | None:
        selected_scopes = list(scopes or self.FLOW_SCOPES.get(flow_type) or self.auth_service.oauth_config["scopes"])
        flow = self.auth_service.build_flow(scopes=selected_scopes) if self.auth_service.oauth_config["client_id"] and self.auth_service.oauth_config["client_secret"] else None
        if flow is None:
            return None
        state_token = self.issue_state_token()
        authorization_url, issued_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state_token,
            code_challenge_method="S256",
        )
        final_state = issued_state or state_token
        st.session_state["oauth_authorization_url"] = authorization_url
        st.session_state["oauth_state_token"] = final_state
        st.session_state["oauth_code_verifier"] = getattr(flow, "code_verifier", None)
        st.session_state["oauth_flow_type"] = flow_type
        st.session_state["oauth_flow_context"] = {
            "flow_type": flow_type,
            "role_context": role_context,
            "manufacturer_id": manufacturer_id,
            "scopes": selected_scopes,
        }
        self._store_pending_state(
            final_state,
            flow_type=flow_type,
            code_verifier=getattr(flow, "code_verifier", None),
            role_context=role_context,
            manufacturer_id=manufacturer_id,
            scopes=selected_scopes,
        )
        self._write_login_url_diagnostic(authorization_url, selected_scopes)
        return authorization_url

    def validate_state(self, returned_state: str | None) -> dict[str, Any]:
        if not returned_state:
            raise PermissionError("OAuth callback state validation failed.")
        pending = self._lookup_pending_state(returned_state)
        if pending:
            st.session_state["oauth_state_token"] = returned_state
            st.session_state["oauth_flow_type"] = pending.get("flow_type")
            st.session_state["oauth_flow_context"] = {
                "flow_type": pending.get("flow_type", ""),
                "role_context": pending.get("role_context", ""),
                "manufacturer_id": pending.get("manufacturer_id", ""),
                "scopes": list(pending.get("scopes", []) or []),
            }
            return pending
        raise PermissionError("OAuth callback state validation failed. Please restart the Google flow.")

    def exchange_code(self, code: str, returned_state: str | None) -> dict[str, Any]:
        pending_state = self.validate_state(returned_state)
        selected_scopes = list(pending_state.get("scopes") or self.auth_service.oauth_config["scopes"])
        flow = self.auth_service.build_flow(scopes=selected_scopes)
        code_verifier = st.session_state.get("oauth_code_verifier") or pending_state.get("code_verifier")
        if code_verifier:
            flow.code_verifier = code_verifier
        flow.fetch_token(code=code)
        consumed = self._consume_pending_state(str(returned_state)) or pending_state
        credentials = flow.credentials
        return {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes or selected_scopes),
            "redirect_uri": self.auth_service.oauth_config["redirect_uri"],
            "flow_type": consumed.get("flow_type", self.LOGIN),
            "role_context": consumed.get("role_context", ""),
            "manufacturer_id": consumed.get("manufacturer_id", ""),
        }

    def reset_authorization_state(self) -> None:
        st.session_state["oauth_authorization_url"] = None
        st.session_state["oauth_state_token"] = None
        st.session_state["oauth_code_verifier"] = None
        st.session_state["oauth_flow_type"] = None
        st.session_state["oauth_flow_context"] = None

    def store_runtime_token(self, principal_key: str, refresh_token: str) -> str:
        target = self.security_service.runtime_tokens_dir / f"{principal_key}.enc"
        self.security_service.encrypt_refresh_token(refresh_token, target=target)
        return str(target)

    def initialize_session(
        self,
        user_payload: dict[str, Any],
        credentials_payload: dict[str, Any],
        manufacturer_code: str | None = None,
        session_source: str = "google_oauth",
    ) -> None:
        if session_source == "mock":
            user = self.auth_service.create_mock_user(
                email=user_payload["email"],
                name=user_payload.get("name", user_payload["email"]),
                role=user_payload["role"],
                manufacturer_code=manufacturer_code,
            )
        elif session_source == "google_oauth":
            token_metadata = {
                "token_uri": credentials_payload.get("token_uri", ""),
                "client_id_present": bool(credentials_payload.get("client_id")),
                "refresh_token_present": bool(credentials_payload.get("refresh_token")),
                "redirect_uri": credentials_payload.get("redirect_uri", ""),
                "flow_type": credentials_payload.get("flow_type", self.LOGIN),
            }
            user = self.auth_service.create_authenticated_user(
                profile=user_payload.get("profile", {}),
                email=user_payload["email"],
                role=user_payload["role"],
                subject_id=user_payload.get("subject_id"),
                manufacturer_code=manufacturer_code,
                granted_scopes=list(user_payload.get("granted_scopes") or credentials_payload.get("scopes") or []),
                token_metadata=token_metadata,
            )
        else:
            raise PermissionError(f"Unsupported session source: {session_source}")
        st.session_state["user"] = self.auth_service.serialize_user(user)
        st.session_state["admin_active_context"] = user.active_context or user.role
        st.session_state["auth_tokens"] = {
            "principal": user.email,
            "role": user.role,
            "base_role": user.base_role,
            "active_context": user.active_context,
            "manufacturer_code": manufacturer_code,
            "session_source": user.session_source,
            "subject_id": user.subject_id,
            "granted_scopes": list(user.granted_scopes or []),
            "token_file": self.store_runtime_token(user.email.replace("@", "_at_"), credentials_payload["refresh_token"]),
        }
        st.session_state["runtime_drive_access"] = {
            "principal": user.email,
            "role": user.role,
            "manufacturer_code": manufacturer_code,
            "restored": True,
            "session_source": user.session_source,
        }
        self.reset_authorization_state()

    def restore_session(self) -> bool:
        auth_tokens = st.session_state.get("auth_tokens")
        user = st.session_state.get("user")
        return bool(auth_tokens and user)

    def capture_failure(
        self,
        *,
        error: str,
        error_description: str = "",
        state: str = "",
    ) -> dict[str, Any]:
        payload = {
            "error": error,
            "error_description": error_description,
            "state": state,
            "client_id_used": self.auth_service.oauth_config.get("client_id", ""),
            "redirect_uri_used": self.auth_service.oauth_config.get("redirect_uri", ""),
            "runtime_environment": self.runtime_environment,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if self.runtime_reports_root:
            self.runtime_reports_root.mkdir(parents=True, exist_ok=True)
            target = self.runtime_reports_root / f"oauth_failure_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            payload["report_path"] = str(target)
        return payload

    def friendly_error_message(self, error: str, error_description: str = "") -> str:
        if error == "disabled_client" or "disabled_client" in error_description.lower():
            return "Google OAuth client is disabled, deleted, or mismatched. Create/enable OAuth Web Client in Google Cloud Console and update Streamlit secrets."
        if error_description.strip():
            return f"OAuth failed: {error_description}"
        return f"OAuth failed: {error}"

    def oauth_debug_snapshot(self) -> dict[str, Any]:
        client_id = str(self.auth_service.oauth_config.get("client_id", "") or "")
        return {
            "client_id_suffix": client_id[-8:] if client_id else "",
            "redirect_uri": self.auth_service.oauth_config.get("redirect_uri", ""),
            "runtime_environment": self.runtime_environment,
            "secrets_override_active": bool(st.session_state.get("oauth_secrets_override_active", False)),
            "oauth_config_fallback_active": bool(st.session_state.get("oauth_config_fallback_active", False)),
        }

    def _write_login_url_diagnostic(self, authorization_url: str, scopes: list[str]) -> dict[str, Any]:
        payload = self.oauth_debug_snapshot()
        parsed = urlparse(authorization_url)
        params = parse_qs(parsed.query)
        payload.update(
            {
                "scope_count": len(scopes),
                "has_code_challenge": bool(params.get("code_challenge")),
                "timestamp": datetime.now(UTC).isoformat(),
                "state_present": bool(params.get("state")),
                "client_id_matches_config": (params.get("client_id", [""])[0] == self.auth_service.oauth_config.get("client_id", "")),
                "redirect_uri_matches_config": (params.get("redirect_uri", [""])[0] == self.auth_service.oauth_config.get("redirect_uri", "")),
            }
        )
        if self.runtime_reports_root:
            self.runtime_reports_root.mkdir(parents=True, exist_ok=True)
            target = self.runtime_reports_root / f"oauth_login_url_diagnostic_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            payload["report_path"] = str(target)
        return payload
