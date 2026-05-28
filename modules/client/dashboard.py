from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_client_dashboard(app_context: dict) -> None:
    current_user = app_context["current_user"]
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
    render_section_intro("Marketplace Overview", "Clients see approved products, order history, and can opt into worker discovery when needed.")
    if orders:
        render_3d_panel("".join(render_mobile_record_card(item) for item in orders[:4]), "Recent Orders")
    st.dataframe(catalog, use_container_width=True)
