from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_metric_button_row


def render_mahajan_dashboard(app_context: dict) -> None:
    user = app_context.get("current_user")
    page_key = "mahajan_dashboard"
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
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": "Supply", "tab_name": "Overview"},
            {"label": "Registry", "value": "Catalog", "tab_name": "Catalog"},
            {"label": "Create", "value": "Add", "tab_name": "Add Raw Material"},
            {"label": "Activity", "value": "Finance", "tab_name": "Activity"},
        ],
    )
    overview_tab, catalog_tab, add_tab, activity_tab = st.tabs(["Overview", "Catalog", "Add Raw Material", "Activity"])
    with overview_tab:
        render_section_intro(
            "Mahajan Role",
            "This workspace is reserved for the admin supply channel. Marketplace management, manufacturers, and client networks remain hidden for this role.",
        )
        st.info("Mahajan access is active. Supply views remain scoped to your admin-linked workflow.")
    with catalog_tab:
        st.info("Raw material catalog is ready for role-safe expansion. Current releases keep this surface summary-first.")
    with add_tab:
        with st.form("mahajan_add_raw_material"):
            name = st.text_input("Raw Material Name")
            category = st.text_input("Category", value="RAW_MATERIAL")
            price = st.number_input("Supply Price", min_value=0.0, step=1.0)
            submitted = st.form_submit_button("Save Raw Material")
        if submitted and name.strip():
            st.success(f"Raw material draft saved for {name.strip()} at {price}.")
    with activity_tab:
        st.info("Admin-linked supply order and ledger activity stays scoped here.")
