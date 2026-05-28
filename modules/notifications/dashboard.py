from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_notifications_dashboard(app_context: dict) -> None:
    render_page_header("Notifications", "In-app alerts and Gmail queue tracking for RFQs, payments, dispatch, and jobs.", ["Notification Center", "Gmail Queue"])
    user = app_context["current_user"]
    notifications = app_context["notification_center_service"].list_notifications(user.manufacturer_code) if user and user.manufacturer_code else []
    queue = app_context["gmail_service"].read_queue()
    render_metric_grid(
        [
            render_metric_card("In-App Alerts", str(len(notifications)), "PENDING"),
            render_metric_card("Gmail Queue", str(len(queue)), "WARNING"),
            render_metric_card("Unread", str(len([item for item in notifications if not item.get("read", False)])), "HIGH_PRIORITY"),
        ]
    )
    if user and user.manufacturer_code:
        render_section_intro("In-App", "Role-relevant alerts stay visible here until read, resolved, or snoozed.")
        if notifications:
            render_3d_panel("".join(render_mobile_record_card(item) for item in notifications[:5]), "Latest Alerts")
        st.dataframe(notifications, use_container_width=True)
    render_section_intro("Gmail Queue", "Ledger reminders and job emails move through the same delivery queue.")
    st.dataframe(queue, use_container_width=True)
    if st.button("Process Queue", use_container_width=True):
        processed = app_context["gmail_service"].process_queue()
        st.success(f"Processed {processed} queued messages.")
