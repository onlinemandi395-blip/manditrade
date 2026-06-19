from __future__ import annotations

from pathlib import Path
from string import Template

import streamlit as st


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


def render_html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def inject_css(path: Path) -> None:
    if path.exists():
        st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def inject_inline_css(css: str) -> None:
    if css.strip():
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def load_template(template_name: str, **context: str) -> str:
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    template_text = template_path.read_text(encoding="utf-8")
    return Template(template_text).safe_substitute(**context)


def render_template(template_name: str, **context: str) -> None:
    render_html(load_template(template_name, **context))
