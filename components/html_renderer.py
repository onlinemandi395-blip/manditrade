from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_html(html: str, *, height: int | None = None) -> None:
    st.markdown(html, unsafe_allow_html=True)


def inject_css(css_path: Path) -> None:
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
