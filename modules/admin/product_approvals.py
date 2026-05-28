from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_product_approvals_dashboard(app_context: dict) -> None:
    product_catalog_service = app_context["product_catalog_service"]
    products = app_context["governance_service"].list_products()
    proposed_products = [item for item in products if item.get("status") == "PROPOSED"]

    render_page_header(
        "Product Approvals",
        "Review manufacturer product proposals and activate only the approved catalog records.",
        ["Platform Admin", "Approval Queue"],
    )
    render_metric_grid(
        [
            render_metric_card("Proposed Products", str(len(proposed_products)), "PENDING"),
            render_metric_card("Active Products", str(len([item for item in products if item.get('status') == 'ACTIVE'])), "SUCCESS"),
            render_metric_card("Rejected Products", str(len([item for item in products if item.get('status') == 'REJECTED'])), "WARNING"),
        ]
    )
    render_section_intro("Approval Queue", "Platform admin captures final mandi price, MRP, and product metadata before activation.")
    st.dataframe(proposed_products, use_container_width=True)
    if not proposed_products:
        st.success("No proposed products are waiting for review.")
        return

    selected_id = st.selectbox("Select Proposed Product", [item["product_id"] for item in proposed_products])
    selected = next(item for item in proposed_products if item["product_id"] == selected_id)
    col1, col2 = st.columns(2)
    mandi_price = col1.number_input("Mandi Price", min_value=0.0, step=1.0, value=float(selected.get("mandi_price", 0) or 0))
    mrp = col2.number_input("MRP", min_value=0.0, step=1.0, value=float(selected.get("mrp", 0) or 0))
    category = col1.text_input("Category", value=selected.get("category", ""))
    unit = col2.text_input("Unit", value=selected.get("unit", "kg"))
    visible = st.checkbox("Visible after approval", value=bool(selected.get("visible", True)))

    approve_col, reject_col = st.columns(2)
    if approve_col.button("Approve Product", use_container_width=True):
        product_catalog_service.approve_product(
            product_id=selected_id,
            approved_by="PLATFORM_ADMIN",
            mandi_price=mandi_price,
            mrp=mrp,
            category=category,
            unit=unit,
            visible=visible,
        )
        st.success("Product approved and activated.")
        st.rerun()
    if reject_col.button("Reject Product", use_container_width=True):
        product_catalog_service.reject_product(product_id=selected_id, approved_by="PLATFORM_ADMIN")
        st.warning("Product marked as rejected.")
        st.rerun()
