from __future__ import annotations

import streamlit as st


def render_payments_dashboard(app_context: dict) -> None:
    st.subheader("Payments")
    user = app_context["current_user"]
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    if st.button("Queue Ledger Reminders", use_container_width=True):
        queued = app_context["ledger_reminder_service"].run_for_manufacturer(user.manufacturer_code, user.email)
        st.success(f"Queued {queued} reminder emails.")
    st.dataframe(app_context["gmail_service"].read_queue(), use_container_width=True)
