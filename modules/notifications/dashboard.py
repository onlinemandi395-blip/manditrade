from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html
from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip
from utils.deep_links import activate_deep_link, build_deep_link_target
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import get_active_filter, render_empty_state, render_metric_button_row


def render_notifications_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    page_key = "notifications"
    render_page_header(
        "Notifications",
        "Stay on top of orders, dispatch, payments, RFQs, and important updates in one place.",
        ["Notification Center", "Email Updates"],
        role=user.role.replace("_", " ").title() if user else "Role Aware",
        metrics=[("Email Updates", "Active"), ("Unread Focus", "Action-led")],
        kicker="Digital Manpur Signal Feed",
    )
    notifications: list[dict] = []
    if user:
        notification_service = app_context["notification_center_service"]
        if user.role == "public_buyer":
            buyer = app_context["public_buyer_service"].get_by_email(user.email)
            if buyer:
                notifications = notification_service.list_public_notifications(buyer["public_buyer_id"])
        elif user.role == "platform_admin":
            for manufacturer in app_context["governance_service"].list_manufacturers():
                notifications.extend(
                    [
                        item
                        for item in notification_service.list_notifications(manufacturer.get("manufacturer_code", ""))
                        if item.get("user_id") in {user.email.lower(), "PLATFORM_ADMIN"}
                    ]
                )
        elif user.manufacturer_code:
            notifications = [
                item
                for item in notification_service.list_notifications(user.manufacturer_code)
                if item.get("user_id") in {user.manufacturer_code, user.email.lower(), user.email}
            ]
    render_metric_grid(
        [
            render_metric_card("In-App Alerts", str(len(notifications)), "PENDING"),
            render_metric_card("Email Updates", "Live", "OPEN"),
            render_metric_card("Unread", str(len([item for item in notifications if not item.get("read", False)])), "HIGH_PRIORITY"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Unread", "value": str(len([item for item in notifications if not item.get("read", False)])), "tab_name": "Unread", "filter_value": "unread"},
            {"label": "All", "value": str(len(notifications)), "tab_name": "All", "filter_value": "all"},
            {"label": "Resolved", "value": str(len([item for item in notifications if item.get("resolved", False)])), "tab_name": "Resolved", "filter_value": "resolved"},
            {"label": "High Priority", "value": str(len([item for item in notifications if str(item.get("priority", "")).upper() == "HIGH"])), "tab_name": "Settings", "filter_value": "high"},
        ],
    )
    render_showcase_strip(
        [
            ("Unread Alerts", str(len([item for item in notifications if not item.get("read", False)])), "HIGH_PRIORITY"),
            ("Trigger Style", "Immediate", "SUCCESS"),
            ("Live Feed", "Dispatch + RFQ + Jobs", "OPEN"),
        ]
    )
    render_dual_panel(
        "Alert Surface",
        render_mobile_record_card({"In-App": len(notifications), "Unread": len([item for item in notifications if not item.get("read", False)])}),
        "Delivery Surface",
        render_mobile_record_card({"Mode": "Live", "Trigger": "Sent during actions"}),
    )
    unread_tab, all_tab, resolved_tab, settings_tab = st.tabs(["Unread", "All", "Resolved", "Settings"])
    active_filter = get_active_filter(page_key).lower()
    with unread_tab:
        if user and (user.manufacturer_code or user.role in {"platform_admin", "public_buyer"}):
            render_section_intro("In-App", "Role-relevant alerts stay visible here until read, resolved, or snoozed.")
            unread_rows = [item for item in notifications if not item.get("read", False)]
            unread_rows = render_filter_bar(
                page_key=f"{page_key}_unread",
                rows=unread_rows,
                search_fields=["notification_id", "title", "message", "type", "source_id"],
                status_field="priority",
                date_field="created_at",
                search_placeholder="Search by notification ID or entity ID",
            )
            preview_cards = "".join(
                f"""
                <article class="mt-glass-card mt-notification-card {'mt-notification-card--unread' if not item.get('read', False) else ''} {'mt-notification-card--resolved' if item.get('resolved', False) else ''}">
                  <div class="mt-notification-card__meta">
                    <div class="mt-chip-row">
                      <span class="mt-badge mt-badge-{escape(str(item.get('priority', 'OPEN')).lower().replace('_', '-'))}">{escape(str(item.get('priority', 'OPEN')))}</span>
                      <span class="mt-chip">{escape(str(item.get('source_type', 'SYSTEM')))}</span>
                    </div>
                    <span class="mt-chip">{escape(str(item.get('type', 'ALERT')))}</span>
                  </div>
                  <h3>{escape(str(item.get('title', 'Notification')))}</h3>
                  <p class="mt-notification-card__message">{escape(str(item.get('message', '')))}</p>
                </article>
                """
                for item in unread_rows[:4]
            )
            if unread_rows:
                render_html(f"<section class='mt-card-stack'>{preview_cards}</section>")
                render_3d_panel("".join(render_mobile_record_card(item) for item in unread_rows[:5]), "Latest Alerts", tone="subtle")
                st.download_button("Download Unread CSV", export_rows_to_csv_bytes(unread_rows), file_name="notifications-unread.csv", mime="text/csv", use_container_width=True)
            else:
                render_empty_state("No notifications need attention right now.")
            st.dataframe(unread_rows, use_container_width=True)
            if unread_rows:
                selected_unread = st.selectbox("Manage Unread Notification", [item["notification_id"] for item in unread_rows], key="notif_unread_select")
                selected_item = next(item for item in unread_rows if item["notification_id"] == selected_unread)
                col1, col2 = st.columns(2)
                if col1.button("Mark Read", key="notif_mark_read", use_container_width=True):
                    _update_notification_status(app_context, user, selected_unread, mark_read=True)
                    st.success("Notification marked read.")
                    st.rerun()
                if col2.button("Open Related Record", key="notif_open_link", use_container_width=True):
                    activate_deep_link(build_deep_link_target(selected_item.get("source_type", ""), selected_item.get("source_id", "")))
                    st.rerun()
            if active_filter == "unread":
                st.caption("Metric filter applied: unread")
        else:
            render_empty_state("No role-specific alerts are available for this session.")
    with all_tab:
        filtered_notifications = render_filter_bar(
            page_key=f"{page_key}_all",
            rows=notifications,
            search_fields=["notification_id", "title", "message", "type", "source_id"],
            status_field="priority",
            date_field="created_at",
            search_placeholder="Search by notification ID, type, or entity ID",
        )
        if filtered_notifications:
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_notifications), file_name="notifications.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_notifications), file_name="notifications.json", mime="application/json", use_container_width=True)
            st.dataframe(filtered_notifications, use_container_width=True)
        else:
            render_empty_state("No notifications match the current filters.")
    with resolved_tab:
        resolved_rows = [item for item in notifications if item.get("resolved", False)]
        if resolved_rows:
            st.dataframe(resolved_rows, use_container_width=True)
        else:
            render_empty_state("No resolved notifications yet.")
    with settings_tab:
        render_section_intro("Notification Controls", "Use these lightweight controls to keep the feed clean without exposing runtime internals.")
        if notifications:
            selected_id = st.selectbox("Select Notification", [item["notification_id"] for item in notifications], key="notif_select")
            selected_item = next(item for item in notifications if item["notification_id"] == selected_id)
            col1, col2 = st.columns(2)
            if col1.button("Mark Resolved", use_container_width=True, key="notif_resolve"):
                _update_notification_status(app_context, user, selected_id, resolved=True)
                st.success("Notification marked resolved.")
                st.rerun()
            if col2.button("Remind Tomorrow", use_container_width=True, key="notif_remind"):
                _update_notification_status(app_context, user, selected_id, remind_later_at="tomorrow")
                st.success("Reminder deferred.")
                st.rerun()
            if st.button("Open Notification Target", use_container_width=True, key="notif_open_target"):
                activate_deep_link(build_deep_link_target(selected_item.get("source_type", ""), selected_item.get("source_id", "")))
                st.rerun()
        st.info("If an email update does not arrive, please contact support.")


def _update_notification_status(app_context: dict, user, notification_id: str, *, mark_read: bool | None = None, resolved: bool | None = None, remind_later_at: str | None = None) -> None:
    service = app_context["notification_center_service"]
    if user.role == "public_buyer":
        buyer = app_context["public_buyer_service"].get_by_email(user.email)
        if buyer:
            service.update_public_status(buyer["public_buyer_id"], notification_id, mark_read=mark_read, resolved=resolved, remind_later_at=remind_later_at)
        return
    manufacturer_code = user.manufacturer_code
    if user.role == "platform_admin" and not manufacturer_code:
        manufacturers = app_context["governance_service"].list_manufacturers()
        for manufacturer in manufacturers:
            try:
                service.update_status(manufacturer.get("manufacturer_code", ""), notification_id, mark_read=mark_read, resolved=resolved, remind_later_at=remind_later_at)
                return
            except ValueError:
                continue
        return
    if manufacturer_code:
        service.update_status(manufacturer_code, notification_id, mark_read=mark_read, resolved=resolved, remind_later_at=remind_later_at)
