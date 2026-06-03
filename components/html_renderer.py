from __future__ import annotations

import re
from pathlib import Path

import streamlit as st


def render_html(html: str, *, height: int | None = None) -> None:
    compact_html = re.sub(r">\s+<", "><", html.strip())
    st.markdown(compact_html, unsafe_allow_html=True)


def inject_css(css_path: Path) -> None:
    injected = st.session_state.setdefault("_injected_css_paths", set())
    css_key = str(css_path.resolve())
    if css_key in injected:
        return
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    injected.add(css_key)
