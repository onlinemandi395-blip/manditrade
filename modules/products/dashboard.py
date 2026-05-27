from __future__ import annotations

import streamlit as st


def render_products_dashboard(app_context: dict) -> None:
    st.subheader("Products")
    user = app_context["current_user"]
    products = app_context["product_catalog_service"].list_products(include_pending=True)
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
