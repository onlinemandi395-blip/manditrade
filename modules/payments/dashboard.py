from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_payments_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Payments", "Send payment reminders and keep follow-up communication organised from one place.", ["Payment Follow-Up", "Email Reminders"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    render_metric_grid(
        [
            render_metric_card("Reminder Channel", "Email", "OPEN"),
            render_metric_card("Trigger", "Send Now", "SUCCESS"),
        ]
    )
    overview_tab, actions_tab = st.tabs(["Overview", "Reminder Actions"])
    with overview_tab:
        render_section_intro("Reminder Engine", "Send reminders for upcoming, due, overdue, and final follow-ups with a clean payment workflow.")
        st.info("If a reminder cannot be sent right now, please try again later or contact support.")
    with actions_tab:
        if st.button("Send Ledger Reminders Now", use_container_width=True):
            triggered = app_context["ledger_reminder_service"].run_for_manufacturer(user.manufacturer_code, user.email)
            st.success(f"Triggered {triggered} reminder emails.")
