from __future__ import annotations

import streamlit as st


class SessionService:
    def __init__(self, app_config: dict) -> None:
        self.app_config = app_config
        st.session_state.setdefault("mt_next_authenticated", False)
        st.session_state.setdefault("mt_next_email", "")
        st.session_state.setdefault("mt_next_role", app_config.get("default_role", "public_buyer"))
        st.session_state.setdefault("mt_next_language", app_config.get("default_language", "en"))
        st.session_state.setdefault("mt_next_route", app_config.get("default_landing", {}).get(st.session_state["mt_next_role"], "marketplace"))

    def is_authenticated(self) -> bool:
        return bool(st.session_state.get("mt_next_authenticated", False))

    def authenticate(self, email: str, role: str, route: str) -> None:
        st.session_state["mt_next_authenticated"] = True
        st.session_state["mt_next_email"] = email
        st.session_state["mt_next_role"] = role
        st.session_state["mt_next_route"] = route

    def logout(self) -> None:
        st.session_state["mt_next_authenticated"] = False
        st.session_state["mt_next_email"] = ""

    def get_role(self) -> str:
        return str(st.session_state.get("mt_next_role", self.app_config.get("default_role", "public_buyer")))

    def set_role(self, role: str) -> None:
        st.session_state["mt_next_role"] = role

    def get_language(self) -> str:
        return str(st.session_state.get("mt_next_language", self.app_config.get("default_language", "en")))

    def set_language(self, language: str) -> None:
        st.session_state["mt_next_language"] = language

    def get_email(self) -> str:
        return str(st.session_state.get("mt_next_email", ""))

    def get_route(self) -> str:
        return str(st.session_state.get("mt_next_route", "dashboard"))

    def set_route(self, route: str) -> None:
        st.session_state["mt_next_route"] = route
