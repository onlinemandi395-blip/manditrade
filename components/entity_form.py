from __future__ import annotations

from contextlib import contextmanager

import streamlit as st


@contextmanager
def render_entity_form(form_key: str, *, title: str | None = None):
    if title:
        st.markdown(f"### {title}")
    with st.form(form_key):
        yield
