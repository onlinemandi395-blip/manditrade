from __future__ import annotations

import streamlit as st

from components.empty_state import render_empty_state


def render_table(rows: list[dict], *, caption: str = "") -> None:
    if caption:
        st.caption(caption)
    if not rows:
        render_empty_state("No rows found.")
        return
    st.dataframe(rows, use_container_width=True)
