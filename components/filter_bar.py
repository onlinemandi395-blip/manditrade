from __future__ import annotations

import streamlit as st


def render_filter_bar(*, route: str) -> dict:
    cols = st.columns([1.4, 1, 1], gap="small")
    sort_by = cols[0].selectbox(
        "Sort By",
        options=["Featured", "Price Low to High", "Price High to Low", "Newest"],
        key=f"{route}_sort_by",
    )
    availability = cols[1].selectbox(
        "Stock",
        options=["All Items", "In Stock"],
        key=f"{route}_availability",
    )
    budget = cols[2].selectbox(
        "Budget",
        options=["Any Budget", "Under Rs. 500", "Rs. 500 to Rs. 2000", "Above Rs. 2000"],
        key=f"{route}_budget_band",
    )
    budget_map = {
        "Any Budget": (0.0, 0.0),
        "Under Rs. 500": (0.0, 500.0),
        "Rs. 500 to Rs. 2000": (500.0, 2000.0),
        "Above Rs. 2000": (2000.0, 0.0),
    }
    min_price, max_price = budget_map.get(budget, (0.0, 0.0))
    return {
        "sort_by": sort_by,
        "availability": availability,
        "min_price": float(min_price or 0),
        "max_price": float(max_price or 0),
    }
