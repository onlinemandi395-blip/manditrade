from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from components.empty_state import render_empty_state
from components.html_renderer import render_html


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_") or "table"


def _format_column_name(name: str) -> str:
    label = str(name).replace("_", " ").strip()
    return label.title() if label else "Value"


def _normalize_rows(rows: list[dict]) -> pd.DataFrame:
    dataframe = pd.DataFrame(rows)
    if dataframe.empty:
        return dataframe
    dataframe = dataframe.fillna("")
    dataframe.columns = [_format_column_name(column) for column in dataframe.columns]
    return dataframe


def _filter_dataframe(dataframe: pd.DataFrame, query: str) -> pd.DataFrame:
    if dataframe.empty or not query.strip():
        return dataframe
    needle = query.strip().lower()
    mask = dataframe.astype(str).apply(lambda column: column.str.lower().str.contains(needle, na=False))
    return dataframe[mask.any(axis=1)]


def render_table(rows: list[dict], *, caption: str = "") -> None:
    title = caption or "Data table"
    table_key = _slugify(title)

    render_html("<div class='mt-table-shell'>")
    header_left, header_right = st.columns([3, 2])
    with header_left:
        st.markdown(f"<div class='mt-table-shell__title'>{title}</div>", unsafe_allow_html=True)
        st.markdown("<div class='mt-table-shell__subtitle'>Browse records in a searchable workspace.</div>", unsafe_allow_html=True)
    with header_right:
        st.markdown(
            (
                "<div class='mt-table-shell__stats'>"
                f"<div><span>Rows</span><strong>{len(rows)}</strong></div>"
                f"<div><span>Columns</span><strong>{len(rows[0]) if rows else 0}</strong></div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    if not rows:
        render_html("</div>")
        render_empty_state("No rows found.")
        return

    dataframe = _normalize_rows(rows)
    query = st.text_input(
        "Search table",
        key=f"{table_key}_search",
        placeholder="Search any value...",
        label_visibility="collapsed",
    )
    filtered = _filter_dataframe(dataframe, query)
    if query.strip() and filtered.empty:
        st.caption(f"No matches found for '{query.strip()}'.")
    else:
        st.caption(f"Showing {len(filtered)} of {len(dataframe)} rows")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    render_html("</div>")
