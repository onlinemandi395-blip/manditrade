from __future__ import annotations

import streamlit as st


def render_empty_state(message: str) -> None:
    st.markdown(f"<div class='mt-empty'>{message}</div>", unsafe_allow_html=True)
