from __future__ import annotations

import streamlit as st

from components.order_timeline import render_order_timeline_component


def render_order_placement(app_context: dict) -> None:
    st.subheader("Order Placement")
    current_user = app_context["current_user"]
    client_service = app_context["client_service"]
    catalog_service = app_context["catalog_service"]
    order_transaction_service = app_context["order_transaction_service"]

    if not current_user or not current_user.manufacturer_code:
        st.info("Client order placement is available after a manufacturer-linked client sign-in.")
        return

    profiles = client_service.list_client_profiles(current_user.manufacturer_code)
    client_profile = next((item for item in profiles if item.get("email", "").lower() == current_user.email.lower()), None)
    if not client_profile:
        st.info("Complete client onboarding before placing an order.")
        return

    catalog = catalog_service.list_active_products()
    if not catalog:
        st.info("No active products available in the catalog.")
        return

    product_map = {f"{item['product_code']} - {item['product_name']}": item for item in catalog}
    selected_label = st.selectbox("Product Catalog", list(product_map.keys()))
    selected_product = product_map[selected_label]
    qty = st.number_input("Quantity", min_value=1, step=1)
    if st.button("Place Order", use_container_width=True):
        order = order_transaction_service.create_order(current_user.manufacturer_code, client_profile, selected_product, int(qty))
        st.success(f"Order {order['order_id']} created with status {order['status']}.")
        render_order_timeline_component(order["status"])
