from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_metric_button_row


def render_analytics_dashboard(app_context: dict) -> None:
    page_key = "analytics"
    render_page_header("Analytics", "Review marketplace, mandi network, and finance summaries from one admin-safe operations page.", ["Platform Admin", "Summary View"])
    current_user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    kpis = app_context["kpi_service"].read_latest_snapshot() or app_context["kpi_service"].calculate_snapshot(app_context)

    if current_user and current_user.role == "manufacturer" and current_user.manufacturer_code:
        orders = app_context["order_query_service"].list_orders(current_user.manufacturer_code)
        procurement = app_context["procurement_query_service"].list_procurement_requests(current_user.manufacturer_code)
        inventory = app_context["inventory_query_service"].list_inventory_snapshot(current_user.manufacturer_code)
        render_metric_grid(
            [
                render_metric_card("Order Volume", str(len(orders)), "OPEN"),
                render_metric_card("Procurement Volume", str(len(procurement)), "PENDING"),
                render_metric_card("Inventory Movements", str(len(inventory.get("items", []))), "SUCCESS"),
            ]
        )
        render_metric_button_row(
            page_key,
            [
                {"label": "Overview", "value": str(len(orders)), "tab_name": "Overview"},
                {"label": "Marketplace", "value": "Own", "tab_name": "Marketplace"},
                {"label": "Mandi Network", "value": str(len(procurement)), "tab_name": "Mandi Network"},
                {"label": "Finance", "value": "Summary", "tab_name": "Finance"},
            ],
        )
        overview_tab, marketplace_tab, mandi_tab, finance_tab = st.tabs(["Overview", "Marketplace", "Mandi Network", "Finance"])
        with overview_tab:
            render_section_intro("Manufacturer Analytics", "This view stays limited to the current manufacturer workspace.")
            st.dataframe(inventory.get("items", []), use_container_width=True)
        with marketplace_tab:
            st.dataframe(app_context["public_order_service"].list_orders_for_seller(current_user.manufacturer_code), use_container_width=True)
        with mandi_tab:
            st.dataframe(procurement, use_container_width=True)
        with finance_tab:
            st.dataframe(app_context["ledger_service"].list_ledger_entries(current_user.manufacturer_code), use_container_width=True)
        return

    manufacturers = governance_service.list_manufacturers()
    products = governance_service.list_products()
    active_manufacturers = len([m for m in manufacturers if m.get("status") == "ACTIVE"])
    blocked_manufacturers = len([m for m in manufacturers if m.get("status") in {"BLOCKED", "INACTIVE"}])
    render_metric_grid(
        [
            render_metric_card("Active Manufacturers", str(active_manufacturers), "SUCCESS"),
            render_metric_card("Marketplace Revenue Today", str(kpis["marketplace"]["revenue_today"]), "OPEN"),
            render_metric_card("Platform Health", str(kpis["health_scores"]["platform"]), "SUCCESS" if kpis["health_scores"]["platform"] >= 70 else "WARNING"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(active_manufacturers), "tab_name": "Overview"},
            {"label": "Marketplace", "value": str(len([p for p in products if p.get('approved_visibility') == 'PUBLIC'])), "tab_name": "Marketplace"},
            {"label": "Mandi Network", "value": str(len(products)), "tab_name": "Mandi Network"},
            {"label": "Finance", "value": "Commission", "tab_name": "Finance"},
        ],
    )
    overview_tab, marketplace_tab, mandi_tab, finance_tab = st.tabs(["Overview", "Marketplace", "Mandi Network", "Finance"])
    with overview_tab:
        render_section_intro("Platform Analytics", "Admin analytics exclude private buyer identities and invoice data.")
        st.dataframe(
            [
                {"metric": "Orders Today", "value": kpis["marketplace"]["orders_today"]},
                {"metric": "Mandi Active Orders", "value": kpis["mandi"]["active_orders"]},
                {"metric": "Outstanding Ledger", "value": kpis["finance"]["outstanding_ledger"]},
                {"metric": "Worker Response Rate", "value": kpis["workforce"]["worker_response_rate"]},
            ],
            use_container_width=True,
        )
    with marketplace_tab:
        public_rows = [item for item in products if item.get("approved_visibility") == "PUBLIC"]
        st.dataframe(public_rows, use_container_width=True)
        top_products = kpis.get("tops", {}).get("products", [])
        if top_products:
            st.bar_chart({item["name"]: item["qty"] for item in top_products})
    with mandi_tab:
        st.dataframe(app_context["governance_service"].list_supply_orders(), use_container_width=True)
        top_materials = kpis.get("tops", {}).get("raw_materials", [])
        if top_materials:
            st.bar_chart({item["raw_material_id"]: item["count"] for item in top_materials})
    with finance_tab:
        st.dataframe(
            [
                {"metric": "Outstanding Ledger", "value": kpis["finance"]["outstanding_ledger"]},
                {"metric": "Overdue %", "value": kpis["finance"]["overdue_percent"]},
                {"metric": "Commission Pending", "value": kpis["finance"]["commission_pending"]},
            ],
            use_container_width=True,
        )
