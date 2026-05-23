from __future__ import annotations

import streamlit as st


def render_notifications_dashboard(app_context: dict) -> None:
    st.subheader("Notifications")
    st.caption("Gmail-only notification architecture.")
    st.write(
        {
            "sender": app_context["system_config"]["notifications"]["admin_sender_email"],
            "gmail_api_enabled": app_context["system_config"]["notifications"]["use_gmail_api"],
        }
    )
    st.markdown("### Queue")
    st.dataframe(app_context["gmail_service"].read_queue(), use_container_width=True)
    if st.button("Process Queue", use_container_width=True):
        processed = app_context["gmail_service"].process_queue()
        st.success(f"Processed {processed} queued messages.")
