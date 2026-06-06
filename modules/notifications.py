from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table


def render_notifications_page(notification_service, data_service, session_service, translator) -> None:
    user = session_service.get_user()
    role = str(user.get("role", "")).strip().lower()
    email = str(user.get("email", "")).strip().lower()
    rows = notification_service.list_notifications_for_user(email, role)

    if role == "platform_admin":
        tab_map = {
            "All": rows,
            "Unread": [row for row in rows if str(row.get("status", "UNREAD")).upper() == "UNREAD"],
            "Products": [row for row in rows if str(row.get("event_type", "")).upper().startswith("PRODUCT")],
            "Orders": [row for row in rows if str(row.get("event_type", "")).upper().startswith("ORDER")],
            "Payments": [row for row in rows if str(row.get("event_type", "")).upper().startswith("PAYMENT")],
            "System": [row for row in rows if str(row.get("event_type", "")).upper().startswith("SYSTEM")],
        }
    else:
        tab_map = {
            "My Notifications": rows,
            "Unread": [row for row in rows if str(row.get("status", "UNREAD")).upper() == "UNREAD"],
            "Read": [row for row in rows if str(row.get("status", "UNREAD")).upper() == "READ"],
        }

    action_cols = st.columns(2)
    if action_cols[0].button("Mark All Mine as Read", use_container_width=True):
        updated = notification_service.mark_all_read_for_user(email, role)
        if updated:
            data_service.persist_collection("notifications")
        st.success(f"{updated} notifications marked as read.")
        st.rerun()

    notification_options = [""] + [str(row.get("notification_id", "")).strip() for row in rows]
    selected_notification_id = action_cols[1].selectbox("Mark Notification Read", options=notification_options, key="notification_mark_read")
    if selected_notification_id and st.button("Mark as Read", use_container_width=True):
        if notification_service.mark_read(selected_notification_id, email, role):
            data_service.persist_collection("notifications")
            st.success("Notification marked as read.")
            st.rerun()
        else:
            st.error("Notification is not visible for current user.")

    tabs = st.tabs(list(tab_map.keys()))
    for tab, (label, filtered_rows) in zip(tabs, tab_map.items()):
        with tab:
            render_table(filtered_rows, caption=label)
