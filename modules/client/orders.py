from __future__ import annotations

import streamlit as st

from components.order_timeline import render_order_timeline_component


def render_client_orders(app_context: dict) -> None:
    current_user = app_context["current_user"]
    st.subheader("Client Orders")
    if not current_user or not current_user.manufacturer_code:
        st.info("Client order history becomes available after a manufacturer-linked sign-in.")
        return

    order_records = app_context["order_query_service"].list_orders_for_client(
        current_user.manufacturer_code,
        current_user.email,
    )
    st.dataframe(order_records, use_container_width=True)
    if order_records:
        selected = st.selectbox("Order Timeline", [order["order_id"] for order in order_records])
        record = next(item for item in order_records if item["order_id"] == selected)
        render_order_timeline_component(record.get("status", "PLACED"))
        comments = st.text_area("Delivery Comments")
        proof_file = st.file_uploader("Delivery Proof", type=["jpg", "jpeg", "png", "pdf"], key=f"delivery-proof-{selected}")
        if st.button("Confirm Delivery", use_container_width=True):
            updated = app_context["order_transaction_service"].confirm_delivery(current_user, selected, comments=comments, proof_file=proof_file)
            closed = app_context["order_transaction_service"].close_order(current_user, selected, reason="Client confirmed delivery")
            st.success(f"Order {closed['order_id']} is now {closed['status']}.")
            st.rerun()
