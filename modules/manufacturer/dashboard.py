from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip
from utils.page_ui import render_metric_button_row


def render_manufacturer_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header(
        "Manufacturer Dashboard",
        "Read-only command view for inventory, orders, sourcing, ledgers, and jobs. Use the dedicated navigation pages to create, update, confirm, or dispatch anything.",
        ["Read Only", "Inventory", "Procurement"],
    )
    if not user or not user.manufacturer_code:
        st.info("Sign in as a manufacturer to view workspace details.")
        return

    inventory = app_context["dual_inventory_service"].list_inventory(user.manufacturer_code)
    orders = app_context["order_query_service"].list_orders(user.manufacturer_code)
    sourcing_requests = app_context["procurement_query_service"].list_procurement_requests(user.manufacturer_code)
    ledgers = app_context["ledger_service"].list_ledgers(user.manufacturer_code)
    jobs = app_context["job_service"].list_jobs(manufacturer_id=user.manufacturer_code)
    marketplace_orders = app_context["public_order_service"].list_orders_for_seller(user.manufacturer_code)

    self_available = sum(int(item.get("self_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))
    mandi_available = sum(int(item.get("mandi_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))
    open_orders = [item for item in orders if item.get("status") not in {"DELIVERED", "CLOSED"}]
    open_jobs = [item for item in jobs if str(item.get("lifecycle_status", "ACTIVE")).upper() == "ACTIVE"]
    pending_ledgers = [item for item in ledgers if str(item.get("status", "")).upper() not in {"PAID", "SETTLED"}]

    render_metric_grid(
        [
            render_metric_card("Self Inventory", str(self_available), "SUCCESS"),
            render_metric_card("Mandi Inventory", str(mandi_available), "OPEN"),
            render_metric_card("Open Orders", str(len(open_orders)), "PENDING"),
            render_metric_card("Open Sourcing", str(len([item for item in sourcing_requests if item.get("status") == "OPEN"])), "WARNING"),
            render_metric_card("Pending Ledgers", str(len(pending_ledgers)), "HIGH_PRIORITY"),
        ]
    )
    render_showcase_strip(
        [
            ("Marketplace Orders", str(len(marketplace_orders)), "SUCCESS"),
            ("Mandi Requests", str(len(sourcing_requests)), "OPEN"),
            ("Active Jobs", str(len(open_jobs)), "PENDING"),
        ]
    )
    render_metric_button_row(
        "manufacturer_dashboard",
        [
            {"label": "Overview", "value": str(len(open_orders)), "tab_name": "Overview"},
            {"label": "Orders", "value": str(len(orders)), "tab_name": "Orders"},
            {"label": "Sourcing", "value": str(len(sourcing_requests)), "tab_name": "Sourcing"},
            {"label": "Finance", "value": str(len(ledgers)), "tab_name": "Finance"},
        ],
    )
    render_section_intro(
        "Read-Only Control View",
        "This dashboard is summary-only. Use Products, Marketplace, MandiPlace, Supply Requests, Payments, Ledger, and Jobs for operational actions.",
    )
    st.caption("Open Suta Mandi Shopping from the `Suta Mandi` navigation page when you want to source yarn items.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Inventory Snapshot")
        st.bar_chart({"Self Inventory": self_available, "Mandi Inventory": mandi_available})
    with col2:
        st.markdown("#### Workload Snapshot")
        st.bar_chart(
            {
                "Open Orders": len(open_orders),
                "Sourcing Requests": len(sourcing_requests),
                "Pending Ledgers": len(pending_ledgers),
                "Active Jobs": len(open_jobs),
            }
        )

    render_dual_panel(
        "Recent Commercial Activity",
        "".join(
            [
                render_mobile_record_card(
                    {
                        "Marketplace Orders": len(marketplace_orders),
                        "Open Mandi Orders": len(open_orders),
                        "Open Supply Requests": len([item for item in sourcing_requests if item.get("status") == "OPEN"]),
                    }
                ),
                render_mobile_record_card(
                    {
                        "Pending Ledgers": len(pending_ledgers),
                        "Jobs": len(open_jobs),
                        "Latest Order State": (open_orders[0].get("status", "NONE") if open_orders else "NONE"),
                    }
                ),
            ]
        ),
        "Latest Read-Only Rows",
        "".join(render_mobile_record_card(item) for item in ledgers[:2]) if ledgers else render_mobile_record_card({"Ledger": "No records", "Status": "Stable"}),
    )

    overview_tab, orders_tab, sourcing_tab, finance_tab = st.tabs(["Overview", "Orders", "Sourcing", "Finance"])
    with overview_tab:
        st.dataframe(
            [
                {
                    "inventory_items": len(inventory.get("items", [])),
                    "self_inventory_qty": self_available,
                    "mandi_inventory_qty": mandi_available,
                    "marketplace_orders": len(marketplace_orders),
                    "open_jobs": len(open_jobs),
                }
            ],
            use_container_width=True,
        )
    with orders_tab:
        st.dataframe(open_orders or orders, use_container_width=True)
    with sourcing_tab:
        st.dataframe(sourcing_requests, use_container_width=True)
    with finance_tab:
        st.dataframe(ledgers, use_container_width=True)
