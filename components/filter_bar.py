from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from utils.filtering import collect_status_options, filter_records


def render_filter_bar(
    *,
    page_key: str,
    rows: list[dict[str, Any]],
    search_fields: list[str] | None = None,
    status_field: str = "status",
    date_field: str = "",
    price_field: str = "",
    search_placeholder: str = "Search by ID, name, or note",
) -> list[dict[str, Any]]:
    status_options = collect_status_options(rows, status_field=status_field)
    col1, col2, col3 = st.columns(3)
    search_query = col1.text_input("Search", key=f"{page_key}_search", placeholder=search_placeholder)
    status_value = col2.selectbox("Status", status_options, key=f"{page_key}_status")
    date_from: date | None = None
    date_to: date | None = None
    if date_field:
        date_from = col3.date_input("From Date", key=f"{page_key}_from_date", value=None)
        date_to = st.columns(1)[0].date_input("To Date", key=f"{page_key}_to_date", value=None)
    min_price = max_price = None
    if price_field:
        price_col1, price_col2 = st.columns(2)
        min_price = price_col1.number_input("Min Price", min_value=0.0, value=0.0, step=1.0, key=f"{page_key}_min_price")
        max_raw = price_col2.number_input("Max Price", min_value=0.0, value=0.0, step=1.0, key=f"{page_key}_max_price")
        min_price = None if min_price <= 0 else min_price
        max_price = None if max_raw <= 0 else max_raw
    return filter_records(
        rows,
        search_query=search_query,
        search_fields=search_fields,
        status_field=status_field,
        status_value=status_value,
        date_field=date_field,
        date_from=date_from,
        date_to=date_to,
        price_field=price_field,
        min_price=min_price,
        max_price=max_price,
    )
