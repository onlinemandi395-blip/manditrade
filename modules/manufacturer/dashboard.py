from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid, render_panel_grid
from components.ui_shell import (
    render_3d_panel,
    render_dual_panel,
    render_metric_card,
    render_mobile_record_card,
    render_page_header,
    render_showcase_strip,
)
from utils.page_ui import render_metric_button_row, set_active_tab_from_metric


def render_manufacturer_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    page_key = "manufacturer_dashboard"
    render_page_header("Manufacturer Dashboard", "Digital Bharat Mandi + Khata + sourcing + inventory + jobs in one operating view.", ["Dual Inventory", "Jobs Network", "Khata"])
    if not user or not user.manufacturer_code:
        st.info("Sign in as a manufacturer to view workspace details.")
        return
    inventory = app_context["dual_inventory_service"].list_inventory(user.manufacturer_code)
    orders = app_context["order_query_service"].list_orders(user.manufacturer_code)
    rfqs = app_context["procurement_query_service"].list_procurement_requests(user.manufacturer_code)
    ledgers = app_context["ledger_service"].list_ledgers(user.manufacturer_code)
    jobs = app_context["job_service"].list_jobs(manufacturer_id=user.manufacturer_code)
    self_available = sum(int(item.get("self_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))
    mandi_available = sum(int(item.get("mandi_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))

    render_metric_grid(
        [
            render_metric_card("Self Inventory", str(self_available), "SUCCESS"),
            render_metric_card("Mandi Inventory", str(mandi_available), "OPEN"),
            render_metric_card("MandiPlace Orders", str(len(orders)), "PENDING"),
            render_metric_card("Open Sourcing Requests", str(len([item for item in rfqs if item.get("status") == "OPEN"])), "WARNING"),
            render_metric_card("Active Jobs", str(len([item for item in jobs if item.get("status") != "COMPLETED"])), "HIGH_PRIORITY"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(len(orders)), "tab_name": "Overview"},
            {"label": "Today", "value": str(len(rfqs)), "tab_name": "Today"},
            {"label": "Pending", "value": str(len([item for item in orders if item.get('status') not in {'DELIVERED', 'CLOSED'}])), "tab_name": "Pending"},
            {"label": "Activity", "value": str(len(ledgers)), "tab_name": "Activity"},
        ],
    )
    render_section_intro(
        "Shopping Navigation",
        "Use `Suta Mandi` from the sidebar to shop admin-curated suta raw materials supplied by mahajans. This is separate from finished Products selling.",
    )
    if st.button("Open Suta Mandi Shopping", use_container_width=True, key="manufacturer_open_suta_mandi"):
        st.session_state["sidebar_section"] = "Suta Mandi"
        set_active_tab_from_metric("suta_mandi", "Catalog")
        st.rerun()
    render_showcase_strip(
        [
            ("Order Pipeline", str(len(orders)), "PENDING"),
            ("Mandi Sourcing", str(len(rfqs)), "OPEN"),
            ("Khata Books", str(len(ledgers)), "WARNING"),
        ]
    )

    render_section_intro("Recent Ledgers", "Keep an eye on B2B and mandi balances before they become overdue.")
    render_dual_panel(
        "Operating Snapshot",
        "".join(
            [
                render_mobile_record_card({"Self Inventory": self_available, "Mandi Inventory": mandi_available}),
                render_mobile_record_card({"Orders": len(orders), "Open Requests": len([item for item in rfqs if item.get("status") == "OPEN"])}),
            ]
        ),
        "Jobs Snapshot",
        "".join(render_mobile_record_card(item) for item in jobs[:2]) if jobs else render_mobile_record_card({"Jobs": "No active jobs", "Status": "Stable"}),
    )
    overview_tab, today_tab, pending_tab, activity_tab = st.tabs(["Overview", "Today", "Pending", "Activity"])
    with overview_tab:
        if ledgers:
            render_3d_panel("".join(render_mobile_record_card(item) for item in ledgers[:4]), "Ledger Snapshot")
        else:
            st.info("No ledger records yet.")
    with today_tab:
        st.dataframe(rfqs, use_container_width=True)
    with pending_tab:
        pending_orders = [item for item in orders if item.get("status") not in {"DELIVERED", "CLOSED"}]
        if pending_orders:
            st.dataframe(pending_orders, use_container_width=True)
        else:
            st.info("No pending manufacturer orders right now.")
    with activity_tab:
        st.dataframe(ledgers, use_container_width=True)
