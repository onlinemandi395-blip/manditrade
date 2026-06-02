from __future__ import annotations

from typing import Any

import streamlit as st


SOURCE_ROUTE_MAP: dict[str, str] = {
    "PUBLIC_ORDER": "Marketplace Orders",
    "RFQ": "Mandi Orders",
    "MANDI_ORDER": "Mandi Orders",
    "SUPPLY_ORDER": "Mandi Orders",
    "JOB": "Jobs",
    "PRODUCT_PROPOSAL": "Products",
    "PAYMENT": "Payments",
    "LEDGER": "Ledger",
}


def build_deep_link_target(source_type: str, source_id: str) -> dict[str, str]:
    normalized = str(source_type or "SYSTEM").strip().upper()
    route = SOURCE_ROUTE_MAP.get(normalized, "Notifications")
    return {"route": route, "source_type": normalized, "source_id": str(source_id or "").strip()}


def activate_deep_link(target: dict[str, Any]) -> None:
    route = str(target.get("route") or "Notifications")
    source_id = str(target.get("source_id") or "").strip()
    source_type = str(target.get("source_type") or "").strip().upper()
    st.session_state["sidebar_section"] = route
    if route == "Marketplace Orders" and source_id:
        st.session_state["deep_link::marketplace_orders"] = source_id
    if route == "Mandi Orders" and source_id:
        st.session_state["deep_link::mandi_orders"] = source_id
    if route == "Jobs" and source_id:
        st.session_state["deep_link::jobs"] = source_id
    if route == "Products" and source_id:
        st.session_state["deep_link::products"] = source_id
    if route == "Payments" and source_id:
        st.session_state["deep_link::payments"] = source_id
    if route == "Ledger" and source_id:
        st.session_state["deep_link::ledger"] = source_id
    st.session_state["deep_link::last_source_type"] = source_type
