from __future__ import annotations

import streamlit as st


def render_orders_dashboard(app_context: dict) -> None:
    st.subheader("Client Orders")
    user = app_context["current_user"]
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    orders = app_context["order_query_service"].list_orders(user.manufacturer_code)
    st.dataframe(orders, use_container_width=True)
