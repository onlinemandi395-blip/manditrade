from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_commission_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header(
        "Platform Commission",
        "Understand how platform commission works across approved pricing channels for your business.",
        ["Commission Overview", "Pricing Policy"],
        role=user.role.replace("_", " ").title() if user else "Finance",
    )
    render_metric_grid(
        [
            render_metric_card("Channel Pricing", "Approved", "SUCCESS"),
            render_metric_card("Settlement Model", "Policy based", "OPEN"),
            render_metric_card("Review Surface", "Finance summary", "PENDING"),
        ]
    )
    render_section_intro(
        "Commission Overview",
        "Commission is calculated from approved channel pricing and your active plan. For exact settlement questions, review your finance records or contact platform support.",
    )
    st.info("Commission details are governed by approved pricing and plan rules.")
