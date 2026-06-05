from __future__ import annotations

import streamlit as st


class SessionService:
    def __init__(self, app_config: dict) -> None:
        self.app_config = app_config
        st.session_state.setdefault(
            "mt_next_user",
            {
                "is_authenticated": False,
                "email": "",
                "role": app_config.get("default_role", "public_buyer"),
                "status": "ACTIVE",
                "display_name": "",
                "landing_page": app_config.get("default_landing", {}).get(app_config.get("default_role", "public_buyer"), "marketplace"),
            },
        )
        st.session_state.setdefault("mt_next_language", app_config.get("default_language", "en"))
        st.session_state.setdefault("mt_next_route", st.session_state["mt_next_user"].get("landing_page", "marketplace"))

    def is_authenticated(self) -> bool:
        return bool(self.get_user().get("is_authenticated", False))

    def get_user(self) -> dict:
        return dict(st.session_state.get("mt_next_user", {}))

    def authenticate(self, user: dict) -> None:
        st.session_state["mt_next_user"] = {
            "is_authenticated": True,
            "email": str(user.get("email", "")).strip().lower(),
            "role": str(user.get("role", self.app_config.get("default_role", "public_buyer"))),
            "status": str(user.get("status", "ACTIVE")),
            "display_name": str(user.get("display_name", "")),
            "landing_page": str(user.get("landing_page", "marketplace")),
        }
        st.session_state["mt_next_route"] = st.session_state["mt_next_user"]["landing_page"]

    def logout(self) -> None:
        st.session_state["mt_next_user"] = {
            "is_authenticated": False,
            "email": "",
            "role": self.app_config.get("default_role", "public_buyer"),
            "status": "ACTIVE",
            "display_name": "",
            "landing_page": self.app_config.get("default_landing", {}).get(self.app_config.get("default_role", "public_buyer"), "marketplace"),
        }
        st.session_state["mt_next_route"] = st.session_state["mt_next_user"]["landing_page"]

    def get_user_role(self) -> str:
        return str(self.get_user().get("role", self.app_config.get("default_role", "public_buyer")))

    def get_language(self) -> str:
        return str(st.session_state.get("mt_next_language", self.app_config.get("default_language", "en")))

    def set_language(self, language: str) -> None:
        st.session_state["mt_next_language"] = language

    def get_email(self) -> str:
        return str(self.get_user().get("email", ""))

    def get_route(self) -> str:
        return str(st.session_state.get("mt_next_route", self.get_user().get("landing_page", "marketplace")))

    def set_route(self, route: str) -> None:
        st.session_state["mt_next_route"] = route

    def get_current_route_or_landing(self) -> str:
        route = self.get_route()
        return route or str(self.get_user().get("landing_page", "marketplace"))
