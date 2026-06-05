from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def inject_css(path: Path) -> None:
    if path.exists():
        st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
