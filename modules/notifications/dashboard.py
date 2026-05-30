from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip


def render_notifications_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header(
        "Notifications",
        "In-app alerts and runtime Gmail triggers for RFQs, payments, dispatch, and jobs.",
        ["Notification Center", "Runtime Gmail"],
        role=user.role.replace("_", " ").title() if user else "Role Aware",
        metrics=[("Trigger Mode", "Immediate runtime"), ("Unread Focus", "Action-led")],
        kicker="Digital Manpur Signal Feed",
    )
    notifications: list[dict] = []
    if user:
        notification_service = app_context["notification_center_service"]
        if user.role == "platform_admin":
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
            render_metric_card("Gmail Mode", app_context["gmail_service"].describe_mode().upper(), "OPEN"),
            render_metric_card("Unread", str(len([item for item in notifications if not item.get("read", False)])), "HIGH_PRIORITY"),
        ]
    )
    render_showcase_strip(
        [
            ("Unread Alerts", str(len([item for item in notifications if not item.get("read", False)])), "HIGH_PRIORITY"),
            ("Trigger Style", "Runtime", "SUCCESS"),
            ("Live Feed", "Dispatch + RFQ + Jobs", "OPEN"),
        ]
    )
    render_dual_panel(
        "Alert Surface",
        render_mobile_record_card({"In-App": len(notifications), "Unread": len([item for item in notifications if not item.get("read", False)])}),
        "Delivery Surface",
        render_mobile_record_card({"Mode": app_context["gmail_service"].describe_mode().upper(), "Trigger": "Immediate runtime send"}),
    )
    alerts_tab, delivery_tab = st.tabs(["In-App Alerts", "Runtime Delivery"])
    with alerts_tab:
        if user and (user.manufacturer_code or user.role == "platform_admin"):
            render_section_intro("In-App", "Role-relevant alerts stay visible here until read, resolved, or snoozed.")
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
                for item in notifications[:4]
            )
            if notifications:
                render_html(f"<section class='mt-card-stack'>{preview_cards}</section>")
                render_3d_panel("".join(render_mobile_record_card(item) for item in notifications[:5]), "Latest Alerts", tone="subtle")
            st.dataframe(notifications, use_container_width=True)
        else:
            st.info("No role-specific alerts are available for this session.")
    with delivery_tab:
        render_section_intro("Runtime Delivery", "Gmail notifications fire immediately from the active runtime session when actions trigger them. There is no user-facing queue.")
        st.info("Notification emails are triggered live during the action itself. Review System Health for runtime failures if a send does not complete.")
