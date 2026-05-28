from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_ledger_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Ledger / Khata", "Keep bilateral udhar simple: due amount, paid amount, balance, reminders, and notes.", ["Khata", "Due Dates", "Reminder History"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    ledgers = app_context["ledger_service"].list_ledgers(user.manufacturer_code)
    pending_entries = sum(1 for ledger in ledgers for entry in ledger.get("entries", []) if entry.get("status") == "PENDING")
    render_metric_grid(
        [
            render_metric_card("Ledger Books", str(len(ledgers)), "SUCCESS"),
            render_metric_card("Pending Entries", str(pending_entries), "OVERDUE" if pending_entries else "SUCCESS"),
        ]
    )
    render_section_intro("Khata Snapshot", "Both mandi trade and client supply dues stay visible here without turning the product into full accounting software.")
    if ledgers:
        render_3d_panel("".join(render_mobile_record_card(item) for item in ledgers[:4]), "Latest Ledger Relationships")
    st.dataframe(ledgers, use_container_width=True)
