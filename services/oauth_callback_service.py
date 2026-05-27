from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

from services.auth_service import AuthService
from services.security_service import SecurityService


class OAuthCallbackService:
    def __init__(self, auth_service: AuthService, security_service: SecurityService, state_store_path: Path | None = None) -> None:
        self.auth_service = auth_service
        self.security_service = security_service
        self.state_store_path = state_store_path

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

    def _store_pending_state(self, token: str, code_verifier: str | None = None) -> None:
        payload = self._read_state_store()
        states = payload.setdefault("states", [])
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        states[:] = [
            item for item in states
            if item.get("token") and datetime.fromisoformat(item.get("created_at", datetime.now(UTC).isoformat())) >= cutoff
        ]
        states.append(
            {
                "token": token,
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

    def _list_recent_pending_states(self) -> list[dict[str, Any]]:
        payload = self._read_state_store()
        states = payload.setdefault("states", [])
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        recent: list[dict[str, Any]] = []
        for item in states:
            created_at_raw = item.get("created_at", datetime.now(UTC).isoformat())
            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                continue
            if created_at >= cutoff and item.get("token"):
                recent.append(item)
        recent.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return recent

    def _has_recent_pending_state(self, token: str | None) -> bool:
        if not token:
            return False
        return self._lookup_pending_state(token) is not None

    def _consume_pending_state(self, token: str) -> bool:
        payload = self._read_state_store()
        states = payload.setdefault("states", [])
        matched = False
        remaining = []
        cutoff = datetime.now(UTC) - timedelta(minutes=15)
        for item in states:
            created_at_raw = item.get("created_at", datetime.now(UTC).isoformat())
            try:
                created_at = datetime.fromisoformat(created_at_raw)
            except ValueError:
                created_at = datetime.now(UTC)
            if created_at < cutoff:
                continue
            if item.get("token") == token and not matched:
                matched = True
                continue
            remaining.append(item)
        payload["states"] = remaining
        self._write_state_store(payload)
        return matched

    def issue_state_token(self) -> str:
        token = secrets.token_urlsafe(24)
        st.session_state["oauth_state_token"] = token
        return token

    def build_authorization_url(self) -> str | None:
        existing_url = st.session_state.get("oauth_authorization_url")
        existing_state = st.session_state.get("oauth_state_token")
        existing_verifier = st.session_state.get("oauth_code_verifier")
        if existing_url and existing_state and existing_verifier and self._has_recent_pending_state(existing_state):
            return existing_url
        if existing_url and existing_state and existing_verifier:
            self.reset_authorization_state()
        flow = self.auth_service.build_flow() if self.auth_service.oauth_config["client_id"] and self.auth_service.oauth_config["client_secret"] else None
        if flow is None:
            return None
        requested_state = self.issue_state_token()
        authorization_url, issued_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=requested_state,
            code_challenge_method="S256",
        )
        final_state = issued_state or requested_state
        st.session_state["oauth_state_token"] = final_state
        st.session_state["oauth_code_verifier"] = getattr(flow, "code_verifier", None)
        st.session_state["oauth_authorization_url"] = authorization_url
        self._store_pending_state(final_state, getattr(flow, "code_verifier", None))
        return authorization_url

    def validate_state(self, returned_state: str | None) -> str:
        expected = st.session_state.get("oauth_state_token")
        if not returned_state:
            raise PermissionError("OAuth callback state validation failed.")
        if expected and expected == returned_state:
            return returned_state
        if self._lookup_pending_state(returned_state):
            st.session_state["oauth_state_token"] = returned_state
            return returned_state
        recent_states = self._list_recent_pending_states()
        recent_tokens = [item.get("token", "") for item in recent_states[:3]]
        raise PermissionError(
            "OAuth callback state validation failed. Please restart sign-in and use a fresh Google authorization link."
            + (f" Recent pending states: {recent_tokens}" if recent_tokens else "")
        )

    def exchange_code(self, code: str, returned_state: str | None) -> dict[str, Any]:
        effective_state = self.validate_state(returned_state)
        flow = self.auth_service.build_flow()
        pending_state = self._lookup_pending_state(effective_state)
        code_verifier = st.session_state.get("oauth_code_verifier") or (pending_state or {}).get("code_verifier")
        if code_verifier:
            flow.code_verifier = code_verifier
        redirect_uri = self.auth_service.oauth_config["redirect_uri"]
        flow.fetch_token(code=code)
        self._consume_pending_state(effective_state)
        credentials = flow.credentials
        payload = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes or []),
            "redirect_uri": redirect_uri,
        }
        return payload

    def reset_authorization_state(self) -> None:
        st.session_state["oauth_authorization_url"] = None
        st.session_state["oauth_state_token"] = None
        st.session_state["oauth_code_verifier"] = None

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
        st.session_state["auth_tokens"] = {
            "principal": user.email,
            "role": user.role,
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
