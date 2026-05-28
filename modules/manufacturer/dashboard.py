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


def render_manufacturer_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Manufacturer Dashboard", "Digital Bharat Mandi + Khata + RFQ + Inventory + Jobs Network in one operating view.", ["Dual Inventory", "Jobs Network", "Khata"])
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
            render_metric_card("Client Orders", str(len(orders)), "PENDING"),
            render_metric_card("Open RFQs", str(len([item for item in rfqs if item.get("status") == "OPEN"])), "WARNING"),
            render_metric_card("Active Jobs", str(len([item for item in jobs if item.get("status") != "COMPLETED"])), "HIGH_PRIORITY"),
        ]
    )
    render_showcase_strip(
        [
            ("Order Pipeline", str(len(orders)), "PENDING"),
            ("Mandi Sourcing", str(len(rfqs)), "OPEN"),
            ("Khata Books", str(len(ledgers)), "WARNING"),
        ]
    )

    render_section_intro("Recent Ledgers", "Keep an eye on client and mandi balances before they become overdue.")
    render_dual_panel(
        "Operating Snapshot",
        "".join(
            [
                render_mobile_record_card({"Self Inventory": self_available, "Mandi Inventory": mandi_available}),
                render_mobile_record_card({"Orders": len(orders), "Open RFQs": len([item for item in rfqs if item.get("status") == "OPEN"])}),
            ]
        ),
        "Jobs Snapshot",
        "".join(render_mobile_record_card(item) for item in jobs[:2]) if jobs else render_mobile_record_card({"Jobs": "No active jobs", "Status": "Stable"}),
    )
    if ledgers:
        render_3d_panel("".join(render_mobile_record_card(item) for item in ledgers[:4]), "Ledger Snapshot")
    st.dataframe(ledgers, use_container_width=True)
