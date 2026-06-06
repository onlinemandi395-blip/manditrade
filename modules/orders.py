from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table


def _tabs_for_role(role: str) -> dict[str, callable]:
    pending_statuses = {"PLACED", "REQUESTED", "PENDING", "IN_PROGRESS"}
    completed_statuses = {"COMPLETED", "DELIVERED", "CLOSED"}
    if role == "platform_admin":
        return {
            "All Orders": lambda rows: rows,
            "Marketplace": lambda rows: [row for row in rows if row.get("source_channel") == "marketplace"],
            "MandiTrade": lambda rows: [row for row in rows if row.get("source_channel") == "manditrade"],
            "New": lambda rows: [row for row in rows if str(row.get("admin_status", "")).upper() == "NEW"],
            "In Progress": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in pending_statuses],
            "Completed": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in completed_statuses],
        }
    if role in {"manufacturer", "mahajan"}:
        return {
            "Requested Orders": lambda rows: [row for row in rows if str(row.get("owner_status", "")).upper() == "PENDING"],
            "Accepted": lambda rows: [row for row in rows if str(row.get("owner_status", "")).upper() == "ACCEPTED"],
            "In Progress": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in {"IN_PROGRESS"}],
            "Completed": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in completed_statuses],
        }
    return {
        "My Orders": lambda rows: rows,
    }


def render_orders_page(rows: list[dict], role: str) -> None:
    tab_map = _tabs_for_role(role)
    tabs = st.tabs(list(tab_map.keys()))
    for tab, (label, filter_fn) in zip(tabs, tab_map.items()):
        with tab:
            render_table(filter_fn(rows), caption=label)
