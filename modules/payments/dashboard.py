from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_metric_button_row


def render_payments_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    page_key = "payments"
    render_page_header("Payments", "Track direct seller/supplier payments and keep follow-up communication organised from one place.", ["Payment Follow-Up", "Email Reminders"])
    if not user:
        st.info("Sign in required.")
        return
    manufacturer_code = user.manufacturer_code or ""
    reminder_ready = bool(manufacturer_code and user.role in {"manufacturer", "admin_as_manufacturer"})
    render_metric_grid(
        [
            render_metric_card("Reminder Channel", "Email", "OPEN"),
            render_metric_card("Trigger", "Send Now" if reminder_ready else "View Only", "SUCCESS"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Pending", "value": "Follow-up", "tab_name": "Pending"},
            {"label": "Verified", "value": "History", "tab_name": "Verified"},
            {"label": "Disputed", "value": "Review", "tab_name": "Failed/Disputed"},
        ],
    )
    overview_tab, pending_tab, verified_tab, disputed_tab = st.tabs(["Overview", "Pending", "Verified", "Failed/Disputed"])
    with overview_tab:
        render_section_intro("Direct Payment Model", "Payments go directly to the seller, manufacturer, or supplier. Platform admin supervises commission and status but is not the default payment receiver.")
        st.info("This page stays role-safe: buyers and workers get payment visibility, while reminder triggers stay limited to manufacturer-linked sessions.")
    with pending_tab:
        if user.role == "mahajan":
            mahajan = app_context["governance_service"].get_mahajan_by_email(user.email)
            entries = [
                item
                for item in app_context["governance_service"].list_supply_ledger_entries()
                if item.get("mahajan_id") == (mahajan or {}).get("mahajan_id")
            ]
            st.dataframe(entries, use_container_width=True)
            return
        if user.role == "platform_admin":
            st.dataframe(app_context["governance_service"].list_supply_ledger_entries(), use_container_width=True)
            return
        if manufacturer_code:
            st.info("Pending verification and reminder-sensitive items are handled through ledger and order workflows.")
        else:
            st.info("No manufacturer-linked pending payment workflow is available for this session.")
        if reminder_ready and st.button("Send Ledger Reminders Now", use_container_width=True):
            triggered = app_context["ledger_reminder_service"].run_for_manufacturer(user.manufacturer_code, user.email)
            st.success(f"Triggered {triggered} reminder emails.")
    with verified_tab:
        st.info("Verified payment history is surfaced in role-specific order and ledger views.")
    with disputed_tab:
        st.info("Failed or disputed payments remain review-only until a dedicated dispute workflow is introduced.")
