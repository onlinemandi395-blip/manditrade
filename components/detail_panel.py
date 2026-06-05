from __future__ import annotations

import streamlit as st


def render_detail_panel(title: str, payload: dict) -> None:
    with st.expander(title, expanded=False):
        st.json(payload)
