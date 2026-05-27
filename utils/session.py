from __future__ import annotations

import time

import streamlit as st


def ensure_session_defaults() -> None:
    defaults = {
        "user": None,
        "auth_tokens": None,
        "nav_section": "Dashboard",
        "flash_message": None,
        "admin_runtime_unlocked": False,
        "runtime_drive_access": None,
        "oauth_authorization_url": None,
        "oauth_state_token": None,
        "oauth_code_verifier": None,
        "manufacturer_context": None,
        "session_last_seen": time.time(),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state["session_last_seen"] = time.time()


def set_flash(message: str) -> None:
    st.session_state["flash_message"] = message


def pop_flash() -> str | None:
    message = st.session_state.get("flash_message")
    st.session_state["flash_message"] = None
    return message


def clear_runtime_session() -> None:
    st.session_state.clear()
