from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import streamlit as st


class SessionService:
    LANGUAGE_KEY = "mt_language"
    SESSION_QUERY_PARAM = "mt_session"
    SESSION_TTL_SECONDS = 604800
    USER_KEY = "mt_next_user"
    EFFECTIVE_USER_KEY = "mt_next_effective_user"

    def __init__(self, app_config: dict) -> None:
        self.app_config = app_config
        initial_language = self._resolve_initial_language()
        restored_user = self._restore_user_from_query_session(initial_language)
        st.session_state.setdefault(self.USER_KEY, restored_user or self._build_default_user(initial_language))
        st.session_state.setdefault(self.EFFECTIVE_USER_KEY, None)
        if self.LANGUAGE_KEY not in st.session_state:
            st.session_state[self.LANGUAGE_KEY] = initial_language
        elif "mt_next_language" in st.session_state and self.LANGUAGE_KEY not in st.session_state:
            st.session_state[self.LANGUAGE_KEY] = self._normalize_language(
                st.session_state.get("mt_next_language", initial_language)
            )
        st.session_state[self.LANGUAGE_KEY] = self._normalize_language(st.session_state.get(self.LANGUAGE_KEY, initial_language))
        st.session_state["mt_next_language"] = st.session_state[self.LANGUAGE_KEY]
        st.session_state.setdefault("mt_next_route", st.session_state[self.get_active_user_key()].get("landing_page", "marketplace"))
        self._persist_user_session()
        self._sync_language_query_param(st.session_state[self.LANGUAGE_KEY])

    def get_active_user_key(self) -> str:
        effective_user = st.session_state.get(self.EFFECTIVE_USER_KEY)
        if isinstance(effective_user, dict) and effective_user.get("is_authenticated"):
            return self.EFFECTIVE_USER_KEY
        return self.USER_KEY

    def _build_default_user(self, language: str) -> dict:
        default_role = self.app_config.get("default_role", "public_buyer")
        return {
            "is_authenticated": False,
            "email": "",
            "role": default_role,
            "status": "ACTIVE",
            "display_name": "",
            "photo_url": "",
            "oauth_token": {},
            "language": self._normalize_language(language),
            "landing_page": self.app_config.get("default_landing", {}).get(default_role, "marketplace"),
        }

    def _normalize_language(self, language: str) -> str:
        default_language = str(self.app_config.get("default_language", "en") or "en").strip().lower() or "en"
        normalized = str(language or "").strip().lower()
        return normalized or default_language

    def _resolve_initial_language(self) -> str:
        query_language = ""
        try:
            query_language = str(st.query_params.get("lang", "") or "").strip().lower()
        except Exception:
            query_language = ""
        if query_language:
            return self._normalize_language(query_language)
        if "mt_next_language" in st.session_state:
            return self._normalize_language(st.session_state.get("mt_next_language", ""))
        return self._normalize_language(self.app_config.get("default_language", "en"))

    def _sync_language_query_param(self, language: str) -> None:
        try:
            st.query_params["lang"] = self._normalize_language(language)
        except Exception:
            pass

    def _sync_session_query_param(self, token: str) -> None:
        try:
            if str(token or "").strip():
                st.query_params[self.SESSION_QUERY_PARAM] = token
            elif self.SESSION_QUERY_PARAM in st.query_params:
                del st.query_params[self.SESSION_QUERY_PARAM]
        except Exception:
            pass

    def _get_session_secret(self) -> str:
        try:
            if "security" in st.secrets:
                security_section = dict(st.secrets.get("security", {}))
                value = str(
                    security_section.get("public_verification_key", "")
                    or security_section.get("fernet_key", "")
                    or ""
                ).strip()
                if value:
                    return value
            if "google_oauth" in st.secrets:
                oauth_section = dict(st.secrets.get("google_oauth", {}))
                return str(oauth_section.get("client_secret", "") or "").strip()
        except Exception:
            pass
        return "manditrade-session-secret"

    def _urlsafe_b64encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")

    def _urlsafe_b64decode(self, value: str) -> bytes:
        padding = "=" * ((4 - len(value) % 4) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("utf-8"))

    def _sign_session_payload(self, payload: dict) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return hmac.new(self._get_session_secret().encode("utf-8"), raw, hashlib.sha256).hexdigest()

    def _serialize_user_for_session(self, user: dict) -> str:
        payload = {
            "email": str(user.get("email", "")).strip().lower(),
            "role": str(user.get("role", self.app_config.get("default_role", "public_buyer"))),
            "status": str(user.get("status", "ACTIVE")),
            "display_name": str(user.get("display_name", "")),
            "photo_url": str(user.get("photo_url", "")),
            "language": self._normalize_language(user.get("language", self.get_language())),
            "landing_page": str(user.get("landing_page", "marketplace")),
            "ts": int(time.time()),
            "exp": int(time.time()) + self.SESSION_TTL_SECONDS,
        }
        envelope = {"payload": payload, "sig": self._sign_session_payload(payload)}
        return self._urlsafe_b64encode(json.dumps(envelope, separators=(",", ":")).encode("utf-8"))

    def _restore_user_from_query_session(self, initial_language: str) -> dict | None:
        try:
            token = str(st.query_params.get(self.SESSION_QUERY_PARAM, "") or "").strip()
        except Exception:
            token = ""
        if not token:
            return None
        try:
            envelope = json.loads(self._urlsafe_b64decode(token).decode("utf-8"))
            payload = dict(envelope.get("payload", {}) or {})
            signature = str(envelope.get("sig", "") or "")
            if not payload or not signature:
                return None
            expected_signature = self._sign_session_payload(payload)
            if not hmac.compare_digest(signature, expected_signature):
                return None
            expires_at = int(payload.get("exp", 0) or 0)
            if expires_at <= int(time.time()):
                self._sync_session_query_param("")
                return None
            return {
                "is_authenticated": True,
                "email": str(payload.get("email", "")).strip().lower(),
                "role": str(payload.get("role", self.app_config.get("default_role", "public_buyer"))),
                "status": str(payload.get("status", "ACTIVE")),
                "display_name": str(payload.get("display_name", "")),
                "photo_url": str(payload.get("photo_url", "")),
                "oauth_token": {},
                "language": self._normalize_language(payload.get("language", initial_language)),
                "landing_page": str(payload.get("landing_page", "marketplace")),
            }
        except Exception:
            self._sync_session_query_param("")
            return None

    def _persist_user_session(self) -> None:
        user = self.get_authenticated_user()
        if user.get("is_authenticated"):
            self._sync_session_query_param(self._serialize_user_for_session(user))
        else:
            self._sync_session_query_param("")

    def is_authenticated(self) -> bool:
        return bool(self.get_user().get("is_authenticated", False))

    def get_user(self) -> dict:
        effective_user = st.session_state.get(self.EFFECTIVE_USER_KEY)
        if isinstance(effective_user, dict) and effective_user.get("is_authenticated"):
            return dict(effective_user)
        return self.get_authenticated_user()

    def get_authenticated_user(self) -> dict:
        return dict(st.session_state.get(self.USER_KEY, {}))

    def authenticate(self, user: dict) -> None:
        current_language = self.get_language()
        st.session_state[self.USER_KEY] = {
            "is_authenticated": True,
            "email": str(user.get("email", "")).strip().lower(),
            "role": str(user.get("role", self.app_config.get("default_role", "public_buyer"))),
            "status": str(user.get("status", "ACTIVE")),
            "display_name": str(user.get("display_name", "")),
            "photo_url": str(user.get("photo_url", "")),
            "oauth_token": dict(user.get("oauth_token", {}) or {}),
            "language": self._normalize_language(user.get("language", current_language)),
            "landing_page": str(user.get("landing_page", "marketplace")),
        }
        st.session_state[self.EFFECTIVE_USER_KEY] = None
        st.session_state["mt_next_route"] = st.session_state[self.USER_KEY]["landing_page"]
        self._sync_language_query_param(st.session_state[self.USER_KEY]["language"])
        self._persist_user_session()

    def logout(self) -> None:
        st.session_state[self.USER_KEY] = self._build_default_user(self.get_language())
        st.session_state[self.EFFECTIVE_USER_KEY] = None
        st.session_state["mt_next_route"] = st.session_state[self.USER_KEY]["landing_page"]
        self._persist_user_session()

    def set_effective_user(self, user: dict | None) -> None:
        if not user:
            st.session_state[self.EFFECTIVE_USER_KEY] = None
            active_user = self.get_authenticated_user()
            st.session_state["mt_next_route"] = str(active_user.get("landing_page", "marketplace") or "marketplace")
            return
        current_language = self.get_language()
        st.session_state[self.EFFECTIVE_USER_KEY] = {
            "is_authenticated": True,
            "email": str(user.get("email", "")).strip().lower(),
            "role": str(user.get("role", self.app_config.get("default_role", "public_buyer"))),
            "status": str(user.get("status", "ACTIVE")),
            "display_name": str(user.get("display_name", "")),
            "photo_url": str(user.get("photo_url", "")),
            "oauth_token": {},
            "language": self._normalize_language(user.get("language", current_language)),
            "landing_page": str(user.get("landing_page", "marketplace")),
            "acting_as": True,
        }
        st.session_state["mt_next_route"] = st.session_state[self.EFFECTIVE_USER_KEY]["landing_page"]

    def clear_effective_user(self) -> None:
        self.set_effective_user(None)

    def is_acting_as_user(self) -> bool:
        effective_user = st.session_state.get(self.EFFECTIVE_USER_KEY)
        return isinstance(effective_user, dict) and bool(effective_user.get("is_authenticated"))

    def get_user_role(self) -> str:
        return str(self.get_user().get("role", self.app_config.get("default_role", "public_buyer")))

    def get_language(self) -> str:
        return self._normalize_language(
            st.session_state.get(
                self.LANGUAGE_KEY,
                self.get_user().get("language", self.app_config.get("default_language", "en")),
            )
        )

    def set_language(self, language: str) -> None:
        normalized = self._normalize_language(language)
        st.session_state[self.LANGUAGE_KEY] = normalized
        st.session_state["mt_next_language"] = normalized
        current_user = dict(st.session_state.get("mt_next_user", {}) or {})
        if current_user:
            current_user["language"] = normalized
            st.session_state["mt_next_user"] = current_user
        self._persist_user_session()
        self._sync_language_query_param(normalized)

    def get_email(self) -> str:
        return str(self.get_user().get("email", ""))

    def get_route(self) -> str:
        return str(st.session_state.get("mt_next_route", self.get_user().get("landing_page", "marketplace")))

    def set_route(self, route: str) -> None:
        st.session_state["mt_next_route"] = route

    def get_current_route_or_landing(self) -> str:
        route = self.get_route()
        return route or str(self.get_user().get("landing_page", "marketplace"))
