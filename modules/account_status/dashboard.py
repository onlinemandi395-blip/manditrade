from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_account_status_dashboard(
    app_context: dict,
    *,
    title: str = "System Health",
    subtitle: str = "Review your account readiness and current service availability from one simple status page.",
) -> None:
    user = app_context["current_user"]
    render_page_header(
        title,
        subtitle,
        ["Account Status", "Service Updates"],
        role=user.role.replace("_", " ").title() if user else "Status",
    )
    render_metric_grid(
        [
            render_metric_card("Account", "Active" if user else "Sign-in required", "SUCCESS" if user else "PENDING"),
            render_metric_card("Services", "Available", "OPEN"),
            render_metric_card("Support", "Contact MandiTrade", "PENDING"),
        ]
    )
    render_section_intro(
        "Service Status",
        "This page is customer-safe and does not expose platform diagnostics. If you notice an issue, contact support and we will help you quickly.",
    )
    st.info("Your account and service status look good right now.")
