from __future__ import annotations

import streamlit as st


def render_with_error_boundary(title: str, renderer, *args, logging_service=None, **kwargs) -> None:
    try:
        renderer(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        if logging_service:
            logging_service.log_error("ui_render_failures", str(exc), {"title": title})
        st.error("Something went wrong.")
        if st.button(f"Retry {title}", key=f"retry_{title.lower().replace(' ', '_')}", use_container_width=True):
            st.rerun()
        with st.expander("View details", expanded=False):
            st.code(str(exc))
