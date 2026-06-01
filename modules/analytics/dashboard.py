from __future__ import annotations

from collections import Counter

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

    if current_user and current_user.role == "manufacturer" and current_user.manufacturer_code:
        orders = app_context["order_query_service"].list_orders(current_user.manufacturer_code)
        procurement = app_context["procurement_query_service"].list_procurement_requests(current_user.manufacturer_code)
        inventory = app_context["inventory_query_service"].list_inventory_snapshot(current_user.manufacturer_code)
        top_products = Counter()
        for order in orders:
            for item in order.get("items", []):
                top_products[item.get("product_name", item.get("product_id", ""))] += int(item.get("qty", 0))
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
            st.dataframe([{"product": k, "ordered_qty": v} for k, v in top_products.most_common(10)], use_container_width=True)
        with marketplace_tab:
            st.info("Marketplace analytics are shown through your marketplace listings and public orders.")
        with mandi_tab:
            st.dataframe(procurement, use_container_width=True)
        with finance_tab:
            st.info("Finance analytics stay summary-only on this screen.")
        return

    manufacturers = governance_service.list_manufacturers()
    products = governance_service.list_products()
    active_manufacturers = len([m for m in manufacturers if m.get("status") == "ACTIVE"])
    blocked_manufacturers = len([m for m in manufacturers if m.get("status") in {"BLOCKED", "INACTIVE"}])
    render_metric_grid(
        [
            render_metric_card("Active Manufacturers", str(active_manufacturers), "SUCCESS"),
            render_metric_card("Blocked Or Inactive", str(blocked_manufacturers), "WARNING"),
            render_metric_card("Product Registry", str(len(products)), "OPEN"),
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
        render_section_intro("Platform Analytics", "Admin analytics exclude private client identities and invoice data.")
        st.dataframe(manufacturers, use_container_width=True)
    with marketplace_tab:
        st.dataframe([item for item in products if item.get("approved_visibility") == "PUBLIC"], use_container_width=True)
    with mandi_tab:
        st.dataframe(products, use_container_width=True)
    with finance_tab:
        st.info("Finance analytics remain summary-first here. Platform commission details stay on the dedicated commission page.")
