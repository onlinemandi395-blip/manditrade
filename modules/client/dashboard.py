from __future__ import annotations

import streamlit as st


def render_client_dashboard(app_context: dict) -> None:
    st.subheader("Client Dashboard")
    current_user = app_context["current_user"]
    if not current_user or not current_user.manufacturer_code:
        st.info("Client session linked to a manufacturer is required.")
        return
    catalog = app_context["product_catalog_service"].list_products(include_pending=False)
    orders = app_context["order_query_service"].list_orders_for_client(current_user.manufacturer_code, current_user.email)
    col1, col2 = st.columns(2)
    col1.metric("Visible Products", len(catalog))
    col2.metric("My Orders", len(orders))
    st.dataframe(catalog, use_container_width=True)
