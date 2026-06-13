from __future__ import annotations

import streamlit as st


class SessionService:
    LANGUAGE_KEY = "mt_language"

    def __init__(self, app_config: dict) -> None:
        self.app_config = app_config
        initial_language = self._resolve_initial_language()
        st.session_state.setdefault(
            "mt_next_user",
            {
                "is_authenticated": False,
                "email": "",
                "role": app_config.get("default_role", "public_buyer"),
                "status": "ACTIVE",
                "display_name": "",
                "photo_url": "",
                "oauth_token": {},
                "language": initial_language,
                "landing_page": app_config.get("default_landing", {}).get(app_config.get("default_role", "public_buyer"), "marketplace"),
            },
        )
        if self.LANGUAGE_KEY not in st.session_state:
            st.session_state[self.LANGUAGE_KEY] = initial_language
        elif "mt_next_language" in st.session_state and self.LANGUAGE_KEY not in st.session_state:
            st.session_state[self.LANGUAGE_KEY] = self._normalize_language(
                st.session_state.get("mt_next_language", initial_language)
            )
        st.session_state[self.LANGUAGE_KEY] = self._normalize_language(st.session_state.get(self.LANGUAGE_KEY, initial_language))
        st.session_state["mt_next_language"] = st.session_state[self.LANGUAGE_KEY]
        st.session_state.setdefault("mt_next_route", st.session_state["mt_next_user"].get("landing_page", "marketplace"))
        self._sync_language_query_param(st.session_state[self.LANGUAGE_KEY])

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

    def is_authenticated(self) -> bool:
        return bool(self.get_user().get("is_authenticated", False))

    def get_user(self) -> dict:
        return dict(st.session_state.get("mt_next_user", {}))

    def authenticate(self, user: dict) -> None:
        current_language = self.get_language()
        st.session_state["mt_next_user"] = {
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
        st.session_state["mt_next_route"] = st.session_state["mt_next_user"]["landing_page"]
        self._sync_language_query_param(st.session_state["mt_next_user"]["language"])

    def logout(self) -> None:
        st.session_state["mt_next_user"] = {
            "is_authenticated": False,
            "email": "",
            "role": self.app_config.get("default_role", "public_buyer"),
            "status": "ACTIVE",
            "display_name": "",
            "photo_url": "",
            "oauth_token": {},
            "landing_page": self.app_config.get("default_landing", {}).get(self.app_config.get("default_role", "public_buyer"), "marketplace"),
        }
        st.session_state["mt_next_route"] = st.session_state["mt_next_user"]["landing_page"]

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
