from __future__ import annotations

import streamlit as st

from modules.client.orders import render_client_orders
from modules.client.profile import render_client_profile
from modules.orders.placement import render_order_placement
from components.order_timeline import render_order_timeline_component


def render_client_dashboard(app_context: dict) -> None:
    st.subheader("Client Dashboard")
    current_user = app_context["current_user"]
    if not current_user or not current_user.manufacturer_code:
        st.info("Client onboarding, product browsing, and order placement require a client session linked to a manufacturer.")
        return

    catalog = app_context["catalog_service"].list_active_products()
    orders = app_context["order_query_service"].list_orders_for_client(current_user.manufacturer_code, current_user.email)

    col1, col2, col3 = st.columns(3)
    col1.metric("Product Catalog", len(catalog))
    col2.metric("Active Orders", len([item for item in orders if item.get("status") not in {"CLOSED"}]))
    col3.metric("Notifications", len(app_context["gmail_service"].read_queue()))

    st.markdown("### Product Catalog")
    st.dataframe(catalog, use_container_width=True)

    st.markdown("### Place Order")
    render_order_placement(app_context)

    st.markdown("### Active Orders")
    render_client_orders(app_context)

    st.markdown("### Profile")
    render_client_profile(app_context)

    if orders:
        st.markdown("### Latest Order Timeline")
        render_order_timeline_component(orders[-1].get("status", "PLACED"))
