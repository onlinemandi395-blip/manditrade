from __future__ import annotations

import streamlit as st


def render_rfq_dashboard(app_context: dict) -> None:
    st.subheader("Mandi RFQ")
    user = app_context["current_user"]
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    service = app_context["procurement_transaction_service"]
    st.dataframe(service.list_requests(user.manufacturer_code), use_container_width=True)
    st.markdown("### Responses")
    st.dataframe(service.list_responses(user.manufacturer_code), use_container_width=True)
