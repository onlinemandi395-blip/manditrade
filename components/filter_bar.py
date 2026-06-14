from __future__ import annotations

import streamlit as st


def render_filter_bar(*, route: str) -> dict:
    cols = st.columns([1.5, 1, 1, 1], gap="small")
    sort_by = cols[0].selectbox(
        "Sort By",
        options=["Relevance", "Price Low to High", "Price High to Low", "Newest"],
        key=f"{route}_sort_by",
    )
    availability = cols[1].selectbox(
        "Availability",
        options=["All", "In Stock"],
        key=f"{route}_availability",
    )
    min_price = cols[2].number_input("Min Price", min_value=0.0, step=1.0, key=f"{route}_min_price")
    max_price = cols[3].number_input("Max Price", min_value=0.0, step=1.0, key=f"{route}_max_price")
    return {
        "sort_by": sort_by,
        "availability": availability,
        "min_price": float(min_price or 0),
        "max_price": float(max_price or 0),
    }
