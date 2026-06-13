from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table


def render_notifications_page(notification_service, data_service, session_service, translator) -> None:
    t = translator.t if translator else (lambda key: key)
    user = session_service.get_user()
    role = str(user.get("role", "")).strip().lower()
    email = str(user.get("email", "")).strip().lower()
    rows = notification_service.list_notifications_for_user(email, role)

    if role == "platform_admin":
        tab_map = {
            t("ui.all"): rows,
            t("ui.unread"): [row for row in rows if str(row.get("status", "UNREAD")).upper() == "UNREAD"],
            t("module.products.title"): [row for row in rows if str(row.get("event_type", "")).upper().startswith("PRODUCT")],
            t("module.orders.title"): [row for row in rows if str(row.get("event_type", "")).upper().startswith("ORDER")],
            t("module.payments.title"): [row for row in rows if str(row.get("event_type", "")).upper().startswith("PAYMENT")],
            t("ui.system"): [row for row in rows if str(row.get("event_type", "")).upper().startswith("SYSTEM")],
        }
    else:
        tab_map = {
            t("ui.my_notifications"): rows,
            t("ui.unread"): [row for row in rows if str(row.get("status", "UNREAD")).upper() == "UNREAD"],
            t("ui.read"): [row for row in rows if str(row.get("status", "UNREAD")).upper() == "READ"],
        }

    action_cols = st.columns(2)
    if action_cols[0].button(t("ui.mark_all_mine_read"), use_container_width=True):
        updated = notification_service.mark_all_read_for_user(email, role)
        if updated:
            data_service.persist_collection("notifications")
        st.success(f"{updated} {t('ui.notifications_marked_read')}")
        st.rerun()

    notification_options = [""] + [str(row.get("notification_id", "")).strip() for row in rows]
    selected_notification_id = action_cols[1].selectbox(t("ui.mark_notification_read"), options=notification_options, key="notification_mark_read")
    if selected_notification_id and st.button(t("ui.mark_as_read"), use_container_width=True):
        if notification_service.mark_read(selected_notification_id, email, role):
            data_service.persist_collection("notifications")
            st.success(t("ui.notification_marked_read"))
            st.rerun()
        else:
            st.error(t("ui.notification_not_visible"))

    tabs = st.tabs(list(tab_map.keys()))
    for tab, (label, filtered_rows) in zip(tabs, tab_map.items()):
        with tab:
            render_table(filtered_rows, caption=label)
