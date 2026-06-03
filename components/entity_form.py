from __future__ import annotations

from contextlib import contextmanager

import streamlit as st


@contextmanager
def render_entity_form(form_key: str, *, title: str | None = None, session_state_service=None, protect_unsaved: bool = True):
    if protect_unsaved and session_state_service:
        session_state_service.mark_unsaved_changes(form_key)
    st.markdown("<section class='mt-entity-form-wrap'>", unsafe_allow_html=True)
    if title:
        st.markdown(f"### {title}")
    if hasattr(st, "caption"):
        st.caption("You have unsaved changes until this form is saved or reset.")
    else:
        st.markdown("Unsaved changes stay local until this form is saved or reset.")
    with st.form(form_key):
        yield
    st.markdown("</section>", unsafe_allow_html=True)
