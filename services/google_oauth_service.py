from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st


class GoogleOAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    SCOPE = "openid email profile"
    STATE_TTL_SECONDS = 900

    def _get_oauth_config(self) -> dict[str, str]:
        section = dict(st.secrets.get("google_oauth", {})) if "google_oauth" in st.secrets else {}
        if not section and "google" in st.secrets:
            section = dict(st.secrets.get("google", {}))
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
        envelope = {
            "payload": payload,
            "sig": self._sign_state_payload(payload),
        }
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
                "prompt": "select_account",
                "state": state,
            }
        )
        return f"{self.AUTH_URL}?{query}"

    def has_callback(self) -> bool:
        params = st.query_params
        return bool(params.get("code"))

    def get_callback_error(self) -> str:
        return str(st.query_params.get("error", "") or "")

    def exchange_code_for_identity(self) -> dict[str, Any]:
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
            token_data = json.loads(response.read().decode("utf-8"))

        access_token = str(token_data.get("access_token", "") or "")
        if not access_token:
            raise ValueError("Google OAuth token exchange failed.")

        userinfo_request = Request(
            self.USERINFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )
        with urlopen(userinfo_request, timeout=20) as response:
            profile = json.loads(response.read().decode("utf-8"))

        return {
            "email": str(profile.get("email", "")).strip().lower(),
            "display_name": str(profile.get("name", "")).strip(),
            "photo_url": str(profile.get("picture", "")).strip(),
            "email_verified": bool(profile.get("email_verified", False)),
        }

    def get_debug_snapshot(self) -> dict[str, str]:
        return {
            "generated_state": str(st.session_state.get("mt_next_oauth_debug_generated_state", "") or ""),
            "received_state": str(st.session_state.get("mt_next_oauth_debug_received_state", "") or ""),
            "redirect_uri": str(st.session_state.get("mt_next_oauth_debug_redirect_uri", self._get_oauth_config()["redirect_uri"]) or ""),
            "callback_error": self.get_callback_error(),
        }

    def clear_callback_params(self) -> None:
        st.query_params.clear()
