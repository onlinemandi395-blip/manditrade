from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_payments_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Payments", "Queue Gmail reminders for due khata entries and monitor payment communication from one place.", ["Gmail Only", "Reminder Queue"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    queue = app_context["gmail_service"].read_queue()
    render_metric_grid(
        [
            render_metric_card("Queued Emails", str(len(queue)), "WARNING"),
            render_metric_card("Failed Emails", str(len([item for item in queue if item.get("status") == "failed"])), "ERROR"),
        ]
    )
    render_section_intro("Reminder Engine", "Use Gmail reminders for upcoming due, due today, overdue, and final reminder flows.")
    if st.button("Queue Ledger Reminders", use_container_width=True):
        queued = app_context["ledger_reminder_service"].run_for_manufacturer(user.manufacturer_code, user.email)
        st.success(f"Queued {queued} reminder emails.")
    st.dataframe(queue, use_container_width=True)
