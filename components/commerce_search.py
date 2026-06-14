from __future__ import annotations

import streamlit as st


def render_commerce_search(*, route: str, placeholder: str) -> str:
    return str(
        st.text_input(
            "",
            value=str(st.session_state.get(f"{route}_commerce_search_value", "") or ""),
            key=f"{route}_commerce_search_input",
            placeholder=placeholder,
            label_visibility="collapsed",
        )
        or ""
    ).strip().lower()
