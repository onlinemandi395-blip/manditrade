from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.paginated_table import render_paginated_table
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes


def render_data_grid(
    *,
    page_key: str,
    rows: list[dict],
    search_fields: list[str],
    status_field: str | None = None,
    date_field: str | None = None,
    price_field: str | None = None,
    search_placeholder: str = "Search records",
) -> list[dict]:
    filtered = render_filter_bar(
        page_key=page_key,
        rows=rows,
        search_fields=search_fields,
        status_field=status_field,
        date_field=date_field,
        price_field=price_field,
        search_placeholder=search_placeholder,
    )
    if filtered:
        col1, col2 = st.columns(2)
        col1.download_button("Export CSV", export_rows_to_csv_bytes(filtered), file_name=f"{page_key}.csv", mime="text/csv", use_container_width=True)
        col2.download_button("Export JSON", export_rows_to_json_bytes(filtered), file_name=f"{page_key}.json", mime="application/json", use_container_width=True)
        render_paginated_table(page_key=page_key, rows=filtered, search_fields=search_fields, status_field=status_field)
    return filtered
