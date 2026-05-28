from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_orders_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Client Orders", "Track multi-product orders, payment proposals, and order readiness without agreement PDFs.", ["Multi-Product", "Payment Proposal"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    orders = app_context["order_query_service"].list_orders(user.manufacturer_code)
    render_metric_grid(
        [
            render_metric_card("Orders", str(len(orders)), "PENDING"),
            render_metric_card("Ready To Confirm", str(len([item for item in orders if item.get("status") == "READY_TO_CONFIRM"])), "WARNING"),
            render_metric_card("Procurement Required", str(len([item for item in orders if item.get("status") == "PROCUREMENT_REQUIRED"])), "HIGH_PRIORITY"),
        ]
    )
    render_section_intro("Orders Queue", "Use this queue to separate client-ready orders from those that need mandi procurement.")
    if orders:
        render_3d_panel("".join(render_mobile_record_card(item) for item in orders[:4]), "Recent Orders")
    st.dataframe(orders, use_container_width=True)
