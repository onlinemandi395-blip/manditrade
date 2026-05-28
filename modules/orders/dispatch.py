from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_dispatch_management(app_context: dict) -> None:
    render_page_header("Dispatch", "Move confirmed orders into dispatch-ready and dispatched states with proof capture when needed.", ["Dispatch", "Delivery Flow"])
    current_user = app_context["current_user"]
    if not current_user or current_user.role not in {"manufacturer", "admin_as_manufacturer", "platform_admin"} or not current_user.manufacturer_code:
        st.info("Dispatch management is available to signed-in manufacturers.")
        return

    orders = app_context["order_query_service"].list_orders(current_user.manufacturer_code)
    candidates = [order for order in orders if order.get("status") in {"ADVANCE_PENDING", "DISPATCH_READY", "DISPATCHED", "DELIVERED"}]
    render_metric_grid(
        [
            render_metric_card("Dispatch Candidates", str(len(candidates)), "PENDING"),
            render_metric_card("Already Dispatched", str(len([item for item in candidates if item.get("status") == "DISPATCHED"])), "DISPATCHED"),
        ]
    )
    render_section_intro("Dispatch Queue", "Use this view after confirmation to keep delivery movement and proof collection on track.")
    if not candidates:
        st.info("No dispatch-ready orders available.")
        return

    selected_id = st.selectbox("Order", [order["order_id"] for order in candidates])
    selected = next(order for order in candidates if order["order_id"] == selected_id)
    vehicle_number = st.text_input("Vehicle Number")
    driver_name = st.text_input("Driver Name")
    transporter_name = st.text_input("Transporter Name")
    proof_file = st.file_uploader("Dispatch Proof", type=["jpg", "jpeg", "png", "pdf"])

    col1, col2 = st.columns(2)
    if col1.button("Mark Dispatch Ready", use_container_width=True):
        app_context["order_transaction_service"].mark_dispatch_ready(current_user, selected_id)
        st.success("Order marked as dispatch ready.")
        st.rerun()
    if col2.button("Dispatch Order", use_container_width=True):
        app_context["order_transaction_service"].dispatch_order(
            current_user=current_user,
            order_id=selected_id,
            vehicle_number=vehicle_number.strip(),
            driver_name=driver_name.strip(),
            transporter_name=transporter_name.strip(),
            proof_file=proof_file,
        )
        st.success("Order dispatched.")
        st.rerun()
