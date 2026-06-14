from __future__ import annotations

import streamlit as st


def render_category_strip(*, route: str, categories: list[str], selected_category: str = "All") -> str:
    options = ["All"] + [category for category in categories if str(category or "").strip()]
    current_value = selected_category if selected_category in options else "All"
    return st.radio(
        "Category",
        options=options,
        index=options.index(current_value),
        horizontal=True,
        key=f"{route}_category_strip",
        label_visibility="collapsed",
    )
