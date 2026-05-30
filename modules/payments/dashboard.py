from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_payments_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Payments", "Trigger runtime Gmail reminders for due khata entries and monitor payment communication from one place.", ["Gmail Only", "Runtime Trigger"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    render_metric_grid(
        [
            render_metric_card("Delivery Mode", app_context["gmail_service"].describe_mode().upper(), "OPEN"),
            render_metric_card("Trigger", "Immediate Runtime", "SUCCESS"),
        ]
    )
    overview_tab, actions_tab = st.tabs(["Overview", "Reminder Actions"])
    with overview_tab:
        render_section_intro("Reminder Engine", "Use Gmail reminders for upcoming due, due today, overdue, and final reminder flows. Sends are attempted immediately at runtime.")
        st.info("There is no reminder queue. If runtime Gmail cannot send, failures are recorded in system diagnostics.")
    with actions_tab:
        if st.button("Send Ledger Reminders Now", use_container_width=True):
            triggered = app_context["ledger_reminder_service"].run_for_manufacturer(user.manufacturer_code, user.email)
            st.success(f"Triggered {triggered} reminder emails.")
