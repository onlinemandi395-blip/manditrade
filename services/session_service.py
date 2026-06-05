from __future__ import annotations

import streamlit as st


class SessionService:
    def __init__(self, app_config: dict) -> None:
        self.app_config = app_config
        st.session_state.setdefault("mt_next_role", app_config.get("default_role", "public_buyer"))
        st.session_state.setdefault("mt_next_language", app_config.get("default_language", "en"))
        st.session_state.setdefault("mt_next_route", app_config.get("default_landing", {}).get(st.session_state["mt_next_role"], "marketplace"))

    def get_role(self) -> str:
        return str(st.session_state.get("mt_next_role", self.app_config.get("default_role", "public_buyer")))

    def set_role(self, role: str) -> None:
        st.session_state["mt_next_role"] = role

    def get_language(self) -> str:
        return str(st.session_state.get("mt_next_language", self.app_config.get("default_language", "en")))

    def get_route(self) -> str:
        return str(st.session_state.get("mt_next_route", "dashboard"))

    def set_route(self, route: str) -> None:
        st.session_state["mt_next_route"] = route
