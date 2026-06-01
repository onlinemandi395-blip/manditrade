from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_mahajan_dashboard(app_context: dict) -> None:
    user = app_context.get("current_user")
    render_page_header(
        "Mahajan Supply Dashboard",
        "Track admin-linked raw material supply work, mandi orders, and finance visibility without exposing marketplace or manufacturer-private data.",
        ["Supply Network", "Admin Linked"],
        role=(user.role if user else "mahajan").replace("_", " ").title(),
    )
    render_metric_grid(
        [
            render_metric_card("Supply Orders", "Admin linked", "OPEN"),
            render_metric_card("Ledger Scope", "Own supply ledger", "PENDING"),
            render_metric_card("Marketplace Access", "Restricted", "WARNING"),
        ]
    )
    render_section_intro(
        "Mahajan Role",
        "This workspace is reserved for the admin supply channel. Marketplace management, manufacturers, and client networks remain hidden for this role.",
    )
    st.info("Mahajan access is active. Supply views remain scoped to your admin-linked workflow.")
