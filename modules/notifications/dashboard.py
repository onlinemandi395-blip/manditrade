from __future__ import annotations

import streamlit as st


def render_notifications_dashboard(app_context: dict) -> None:
    st.subheader("Notifications")
    st.caption("In-app notification center with Gmail queue for payment reminders.")
    user = app_context["current_user"]
    if user and user.manufacturer_code:
        st.markdown("### In-App")
        st.dataframe(app_context["notification_center_service"].list_notifications(user.manufacturer_code), use_container_width=True)
    st.markdown("### Gmail Queue")
    st.dataframe(app_context["gmail_service"].read_queue(), use_container_width=True)
    if st.button("Process Queue", use_container_width=True):
        processed = app_context["gmail_service"].process_queue()
        st.success(f"Processed {processed} queued messages.")
