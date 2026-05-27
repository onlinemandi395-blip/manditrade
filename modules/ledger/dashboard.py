from __future__ import annotations

import streamlit as st


def render_ledger_dashboard(app_context: dict) -> None:
    st.subheader("Ledger / Khata")
    user = app_context["current_user"]
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    ledgers = app_context["ledger_service"].list_ledgers(user.manufacturer_code)
    st.dataframe(ledgers, use_container_width=True)
