from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header
from utils.page_ui import render_metric_button_row


def render_client_dashboard(app_context: dict) -> None:
    current_user = app_context["current_user"]
    page_key = "client_dashboard"
    if not current_user:
        render_page_header("Client Dashboard", "Track proposals, payments, product discovery, and worker-mode access from one clean view.", ["Client View"])
        st.info("Sign in to access your client workspace.")
        return
    render_page_header("Client Dashboard", "Track proposals, payments, product discovery, and worker-mode access from one clean view.", ["Client View", "Responsive UI"])
    catalog = app_context["product_catalog_service"].list_products(include_pending=False, viewer_role="client")
    orders = app_context["order_query_service"].list_orders_for_client(current_user.manufacturer_code or "", current_user.email)
    worker_profile = app_context["worker_service"].get_worker_by_email(current_user.email)
    render_metric_grid(
        [
            render_metric_card("Visible Products", str(len(catalog)), "SUCCESS"),
            render_metric_card("My Orders", str(len(orders)), "PENDING"),
            render_metric_card("Worker Profile", "Enabled" if worker_profile else "Optional", "OPEN" if worker_profile else "WARNING"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(len(catalog)), "tab_name": "Overview"},
            {"label": "Today", "value": str(len(orders)), "tab_name": "Today"},
            {"label": "Pending", "value": str(len([item for item in orders if item.get('status') not in {'DELIVERED', 'CLOSED'}])), "tab_name": "Pending"},
            {"label": "Activity", "value": "Orders", "tab_name": "Activity"},
        ],
    )
    render_section_intro("Marketplace Overview", "Clients see approved products, order history, and can opt into worker discovery when needed.")
    overview_tab, today_tab, pending_tab, activity_tab = st.tabs(["Overview", "Today", "Pending", "Activity"])
    with overview_tab:
        if orders:
            render_3d_panel("".join(render_mobile_record_card(item) for item in orders[:4]), "Recent Orders")
        st.dataframe(catalog, use_container_width=True)
    with today_tab:
        st.dataframe(orders, use_container_width=True)
    with pending_tab:
        pending_orders = [item for item in orders if item.get("status") not in {"DELIVERED", "CLOSED"}]
        if pending_orders:
            st.dataframe(pending_orders, use_container_width=True)
        else:
            st.info("No pending client orders right now.")
    with activity_tab:
        if worker_profile:
            st.json(worker_profile, expanded=False)
        else:
            st.info("Worker profile is optional for client sessions.")
