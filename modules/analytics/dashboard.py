from __future__ import annotations

import streamlit as st

from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from utils.page_ui import render_metric_button_row


def render_analytics_dashboard(app_context: dict) -> None:
    page_key = "analytics"
    render_platform_shell(
        title="Analytics",
        subtitle="Review marketplace, mandi network, and finance summaries from one admin-safe operations page.",
        badges=["Platform Admin", "Summary View"],
        role=(app_context["current_user"].role.replace("_", " ").title() if app_context.get("current_user") else None),
        breadcrumbs=["Platform", "Analytics"],
    )
    current_user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    settlement_service = app_context.get("settlement_service")
    kpis = app_context["kpi_service"].read_latest_snapshot() or app_context["kpi_service"].calculate_snapshot(app_context)

    if current_user and current_user.role == "manufacturer" and current_user.manufacturer_code:
        orders = app_context["order_query_service"].list_orders(current_user.manufacturer_code)
        procurement = app_context["procurement_query_service"].list_procurement_requests(current_user.manufacturer_code)
        inventory = app_context["inventory_query_service"].list_inventory_snapshot(current_user.manufacturer_code)
        render_kpi_cards(
            [
                {"label": "Order Volume", "value": str(len(orders)), "status": "OPEN"},
                {"label": "Procurement Volume", "value": str(len(procurement)), "status": "PENDING"},
                {"label": "Inventory Movements", "value": str(len(inventory.get("items", []))), "status": "SUCCESS"},
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
            if settlement_service:
                st.dataframe(settlement_service.list_transactions(role="manufacturer", owner_id=current_user.manufacturer_code), use_container_width=True)
            else:
                st.dataframe(app_context["ledger_service"].list_ledger_entries(current_user.manufacturer_code), use_container_width=True)
        return

    manufacturers = governance_service.list_manufacturers()
    products = governance_service.list_products()
    active_manufacturers = len([m for m in manufacturers if m.get("status") == "ACTIVE"])
    blocked_manufacturers = len([m for m in manufacturers if m.get("status") in {"BLOCKED", "INACTIVE"}])
    render_kpi_cards(
        [
            {"label": "Active Manufacturers", "value": str(active_manufacturers), "status": "SUCCESS"},
            {"label": "Marketplace Revenue Today", "value": str(kpis["marketplace"]["revenue_today"]), "status": "OPEN"},
            {"label": "Platform Health", "value": str(kpis["health_scores"]["platform"]), "status": "SUCCESS" if kpis["health_scores"]["platform"] >= 70 else "WARNING"},
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
        rows = [
            {"metric": "Outstanding Ledger", "value": kpis["finance"]["outstanding_ledger"]},
            {"metric": "Overdue %", "value": kpis["finance"]["overdue_percent"]},
            {"metric": "Commission Pending", "value": kpis["finance"]["commission_pending"]},
        ]
        if settlement_service:
            summary = settlement_service.summarize()
            rows.extend(
                [
                    {"metric": "Financial Transactions", "value": summary["transaction_count"]},
                    {"metric": "Finance Outstanding", "value": summary["outstanding_balance"]},
                    {"metric": "Packaging Charges", "value": summary["packaging_amount"]},
                    {"metric": "Courier Charges", "value": summary["courier_amount"]},
                ]
            )
        st.dataframe(rows, use_container_width=True)
