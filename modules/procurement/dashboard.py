from __future__ import annotations

import streamlit as st


def render_procurement_dashboard(app_context: dict) -> None:
    st.subheader("Mandi Orders")
    st.caption("Review manufacturer-to-manufacturer order requests and responses across the mandi network.")
    user = app_context["current_user"]
    if not user:
        st.info("Sign in required.")
        return
    if user.role == "mahajan":
        st.info("Mahajan mandi orders are scoped to admin-linked supply workflows.")
        return
    if not user.manufacturer_code:
        st.info("Manufacturer-linked sign-in required.")
        return
    service = app_context["procurement_transaction_service"]
    st.dataframe(service.list_requests(user.manufacturer_code), use_container_width=True)
