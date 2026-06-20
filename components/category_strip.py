from __future__ import annotations

import streamlit as st


def render_category_strip(*, route: str, categories: list[str], selected_category: str = "All") -> str:
    options = ["All Categories"] + [category for category in categories if str(category or "").strip()]
    current_value = selected_category if selected_category in options else "All Categories"
    return st.selectbox(
        "Category",
        options=options,
        index=options.index(current_value if current_value in options else "All Categories"),
        key=f"{route}_category_strip",
        label_visibility="collapsed",
    )
