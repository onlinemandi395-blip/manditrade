from __future__ import annotations

import streamlit as st


def render_clients_dashboard(app_context: dict) -> None:
    st.subheader("Clients")
    user = app_context["current_user"]
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    st.dataframe(app_context["client_service"].list_clients(user.manufacturer_code), use_container_width=True)
