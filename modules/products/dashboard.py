from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_products_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    products = app_context["product_catalog_service"].list_products(include_pending=True)
    render_page_header("Products", "Govern public mandi catalog, approvals, and pricing without slipping back into ERP complexity.", ["Public Catalog", "Mandi Price", "MRP"])
    render_metric_grid(
        [
            render_metric_card("Catalog Products", str(len(products)), "SUCCESS"),
            render_metric_card("Pending Approval", str(len([item for item in products if item.get("status") == "PENDING_APPROVAL"])), "PENDING"),
            render_metric_card("Active", str(len([item for item in products if item.get("status") == "ACTIVE"])), "OPEN"),
        ]
    )
    render_section_intro("Catalog Governance", "Manufacturers can propose products and platform admin approves them with mandi price and MRP.")
    st.dataframe(products, use_container_width=True)
    if not user or user.role not in {"manufacturer", "admin_as_manufacturer", "platform_admin"}:
        return
    with st.form("propose_product"):
        name = st.text_input("Product Name")
        category = st.text_input("Category")
        unit = st.text_input("Unit", value="kg")
        submitted = st.form_submit_button("Propose Product")
    if submitted and name and category:
        created_by = user.manufacturer_code or "PLATFORM_ADMIN"
        app_context["product_catalog_service"].propose_product(created_by=created_by, name=name, category=category, unit=unit)
        st.success("Product proposal saved.")
        st.rerun()
