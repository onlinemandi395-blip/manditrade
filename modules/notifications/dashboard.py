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
    alerts_tab, delivery_tab = st.tabs(["In-App Alerts", "Email Delivery"])
    with alerts_tab:
        if user and (user.manufacturer_code or user.role in {"platform_admin", "public_buyer"}):
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
        render_section_intro("Email Delivery", "Important updates are sent as actions happen, so your team can respond quickly.")
        st.info("If an email update does not arrive, please contact support.")
