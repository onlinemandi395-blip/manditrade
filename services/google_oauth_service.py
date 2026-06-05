from __future__ import annotations

import json
import secrets
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st


class GoogleOAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    SCOPE = "openid email profile"

    def _get_oauth_config(self) -> dict[str, str]:
        section = dict(st.secrets.get("google_oauth", {})) if "google_oauth" in st.secrets else {}
        if not section and "google" in st.secrets:
            section = dict(st.secrets.get("google", {}))
        return {
            "client_id": str(section.get("client_id", "")).strip(),
            "client_secret": str(section.get("client_secret", "")).strip(),
            "redirect_uri": str(section.get("redirect_uri", "")).strip(),
        }

    def is_configured(self) -> bool:
        config = self._get_oauth_config()
        return bool(config["client_id"] and config["client_secret"] and config["redirect_uri"])

    def get_authorize_url(self) -> str:
        config = self._get_oauth_config()
        state = secrets.token_urlsafe(24)
        st.session_state["mt_next_oauth_state"] = state
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
        state = str(params.get("state", "") or "")
        expected_state = str(st.session_state.get("mt_next_oauth_state", "") or "")
        if not code:
            raise ValueError("Missing OAuth authorization code.")
        if not expected_state or state != expected_state:
            raise ValueError("Invalid OAuth state. Please try signing in again.")

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

    def clear_callback_params(self) -> None:
        st.query_params.clear()
        st.session_state.pop("mt_next_oauth_state", None)
