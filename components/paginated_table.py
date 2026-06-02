from __future__ import annotations

import streamlit as st

from services.query_engine import QueryEngine


def render_paginated_table(
    *,
    page_key: str,
    rows: list[dict],
    search_query: str = "",
    search_fields: list[str] | None = None,
    status_field: str = "status",
    status_value: str = "All",
    sort_by: str = "",
    descending: bool = False,
    page_size: int = 25,
) -> list[dict]:
    page_state_key = f"paginated::{page_key}::page"
    current_page = int(st.session_state.get(page_state_key, 1))
    query = QueryEngine().query(
        rows,
        search_query=search_query,
        search_fields=search_fields,
        status_field=status_field,
        status_value=status_value,
        sort_by=sort_by,
        descending=descending,
        page=current_page,
        page_size=page_size,
    )
    pager_col1, pager_col2, pager_col3 = st.columns([1, 1, 2])
    if pager_col1.button("Previous", key=f"{page_key}_prev", use_container_width=True, disabled=query["page"] <= 1):
        st.session_state[page_state_key] = max(query["page"] - 1, 1)
        st.rerun()
    if pager_col2.button("Next", key=f"{page_key}_next", use_container_width=True, disabled=query["page"] >= query["pages"]):
        st.session_state[page_state_key] = min(query["page"] + 1, query["pages"])
        st.rerun()
    pager_col3.caption(f"Page {query['page']} of {query['pages']} | {query['total']} records")
    st.dataframe(query["rows"], use_container_width=True)
    return list(query["rows"])
