from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st

from services.google_drive_service import GoogleDriveService


class GoogleOAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    SCOPE = "openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/gmail.send"
    STATE_TTL_SECONDS = 900

    def __init__(self) -> None:
        self.token_store_path = Path(__file__).resolve().parent.parent / "runtime" / "oauth" / "admin_user_token.json"
        self.drive_service = GoogleDriveService(self.token_store_path)

    def _get_oauth_config(self) -> dict[str, str]:
        section = dict(st.secrets.get("google_oauth", {})) if "google_oauth" in st.secrets else {}
        return {
            "client_id": str(section.get("client_id", "")).strip(),
            "client_secret": str(section.get("client_secret", "")).strip(),
            "redirect_uri": str(section.get("redirect_uri", "")).strip(),
        }

    def _get_signing_secret(self) -> str:
        if "security" in st.secrets:
            section = dict(st.secrets.get("security", {}))
            value = str(section.get("public_verification_key", "") or section.get("fernet_key", "")).strip()
            if value:
                return value
        config = self._get_oauth_config()
        return config["client_secret"]

    def is_configured(self) -> bool:
        config = self._get_oauth_config()
        return bool(config["client_id"] and config["client_secret"] and config["redirect_uri"])

    def is_debug_enabled(self) -> bool:
        section = dict(st.secrets.get("oauth_debug", {})) if "oauth_debug" in st.secrets else {}
        return bool(section.get("enabled", False))

    def _urlsafe_b64encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")

    def _urlsafe_b64decode(self, value: str) -> bytes:
        padding = "=" * ((4 - len(value) % 4) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("utf-8"))

    def _sign_state_payload(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hmac.new(self._get_signing_secret().encode("utf-8"), raw, hashlib.sha256).hexdigest()

    def _create_state_token(self) -> str:
        config = self._get_oauth_config()
        payload = {
            "nonce": secrets.token_urlsafe(24),
            "ts": int(time.time()),
            "redirect_uri": config["redirect_uri"],
        }
        envelope = {"payload": payload, "sig": self._sign_state_payload(payload)}
        token = self._urlsafe_b64encode(json.dumps(envelope, separators=(",", ":")).encode("utf-8"))
        st.session_state["mt_next_oauth_debug_generated_state"] = token
        st.session_state["mt_next_oauth_debug_redirect_uri"] = config["redirect_uri"]
        return token

    def _parse_and_validate_state_token(self, token: str) -> dict[str, Any]:
        try:
            envelope = json.loads(self._urlsafe_b64decode(token).decode("utf-8"))
        except Exception as exc:
            raise ValueError("Invalid OAuth state token format.") from exc
        payload = envelope.get("payload", {})
        signature = str(envelope.get("sig", "") or "")
        if not payload or not signature:
            raise ValueError("Invalid OAuth state token payload.")
        expected_signature = self._sign_state_payload(payload)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid OAuth state signature.")
        current_redirect_uri = self._get_oauth_config()["redirect_uri"]
        token_redirect_uri = str(payload.get("redirect_uri", "") or "")
        if token_redirect_uri != current_redirect_uri:
            raise ValueError("OAuth redirect URI mismatch.")
        token_ts = int(payload.get("ts", 0) or 0)
        if token_ts <= 0 or (time.time() - token_ts) > self.STATE_TTL_SECONDS:
            raise ValueError("OAuth state expired. Please try signing in again.")
        return payload

    def get_authorize_url(self) -> str:
        config = self._get_oauth_config()
        state = self._create_state_token()
        query = urlencode(
            {
                "client_id": config["client_id"],
                "redirect_uri": config["redirect_uri"],
                "response_type": "code",
                "scope": self.SCOPE,
                "access_type": "offline",
                "include_granted_scopes": "true",
                "prompt": "consent select_account",
                "state": state,
            }
        )
        return f"{self.AUTH_URL}?{query}"

    def has_callback(self) -> bool:
        return bool(st.query_params.get("code"))

    def get_callback_error(self) -> str:
        return str(st.query_params.get("error", "") or "")

    def exchange_code(self) -> dict[str, Any]:
        params = st.query_params
        code = str(params.get("code", "") or "")
        received_state = str(params.get("state", "") or "")
        st.session_state["mt_next_oauth_debug_received_state"] = received_state
        if not code:
            raise ValueError("Missing OAuth authorization code.")
        self._parse_and_validate_state_token(received_state)
        config = self._get_oauth_config()
        payload = urlencode(
            {
                "code": code,
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "redirect_uri": config["redirect_uri"],
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        request = Request(self.TOKEN_URL, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_identity(self, access_token: str) -> dict[str, Any]:
        userinfo_request = Request(self.USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        with urlopen(userinfo_request, timeout=20) as response:
            profile = json.loads(response.read().decode("utf-8"))
        return {
            "email": str(profile.get("email", "")).strip().lower(),
            "display_name": str(profile.get("name", "")).strip(),
            "photo_url": str(profile.get("picture", "")).strip(),
            "email_verified": bool(profile.get("email_verified", False)),
        }

    def exchange_code_for_identity(self) -> dict[str, Any]:
        token_data = self.exchange_code()
        access_token = str(token_data.get("access_token", "") or "")
        if not access_token:
            raise ValueError("Google OAuth token exchange failed.")
        identity = self.get_identity(access_token)
        identity["oauth_token"] = self._normalize_token_payload(token_data)
        return identity

    def _normalize_token_payload(self, token_data: dict[str, Any]) -> dict[str, Any]:
        config = self._get_oauth_config()
        expires_in = int(token_data.get("expires_in", 0) or 0)
        expires_at = ""
        if expires_in:
            expires_at = datetime.now(UTC).timestamp() + expires_in
        return {
            "token": str(token_data.get("access_token", "") or ""),
            "refresh_token": str(token_data.get("refresh_token", "") or ""),
            "token_uri": self.TOKEN_URL,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "scopes": self.SCOPE.split(),
            "expiry": datetime.fromtimestamp(expires_at, UTC).isoformat() if expires_at else "",
        }

    def persist_admin_token(self, identity: dict[str, Any], user: dict[str, Any]) -> None:
        if not user.get("is_primary_admin", False):
            return
        token_payload = dict(identity.get("oauth_token", {}))
        token_payload.update(
            {
                "email": identity.get("email", ""),
                "display_name": identity.get("display_name", ""),
                "photo_url": identity.get("photo_url", ""),
            }
        )
        self.drive_service.write_token_store(token_payload)

    def get_token_from_session(self) -> dict[str, Any]:
        return dict(st.session_state.get("mt_next_user", {}).get("oauth_token", {}) or {})

    def get_debug_snapshot(self) -> dict[str, str]:
        return {
            "generated_state": str(st.session_state.get("mt_next_oauth_debug_generated_state", "") or ""),
            "received_state": str(st.session_state.get("mt_next_oauth_debug_received_state", "") or ""),
            "redirect_uri": str(st.session_state.get("mt_next_oauth_debug_redirect_uri", self._get_oauth_config()["redirect_uri"]) or ""),
            "callback_error": self.get_callback_error(),
        }

    def clear_callback_params(self) -> None:
        st.query_params.clear()
