from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state, render_metric_button_row


def render_ledger_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    page_key = "ledger"
    render_page_header(
        "Ledger / Khata",
        "Keep sales, procurement, outstanding balance, margin visibility, and settlement notes in one place without pretending the platform is a payment gateway.",
        ["Khata", "Margin View", "Settlement Notes"],
        role=user.role.replace("_", " ").title() if user else "Manufacturer View",
        metrics=[("Readability", "High contrast"), ("Motion", "Minimal by design")],
        kicker="Digital Manpur Ledger Surface",
    )
    if not user:
        st.info("Sign in required.")
        return
    if user.role == "mahajan":
        mahajan = app_context["governance_service"].get_mahajan_by_email(user.email)
        ledgers = [
            item
            for item in app_context["governance_service"].list_supply_ledger_entries()
            if item.get("mahajan_id") == (mahajan or {}).get("mahajan_id")
        ]
        pending_entries = len([item for item in ledgers if item.get("status") in {"PENDING", "PARTIAL", "OVERDUE"}])
        overdue_entries = 0
    elif user.role == "platform_admin":
        ledgers = app_context["governance_service"].list_supply_ledger_entries()
        pending_entries = len([item for item in ledgers if item.get("status") in {"PENDING", "PARTIAL", "OVERDUE"}])
        overdue_entries = 0
    else:
        if not user.manufacturer_code:
            st.info("Manufacturer-linked session required.")
            return
        ledgers = app_context["ledger_service"].list_ledgers_for_role(user.manufacturer_code, user.role)
        pending_entries = sum(1 for ledger in ledgers for entry in ledger.get("entries", []) if entry.get("status") in {"PENDING", "PARTIAL", "OVERDUE"})
        overdue_entries = sum(1 for ledger in ledgers for entry in ledger.get("entries", []) if entry.get("status") == "OVERDUE")
    render_metric_grid(
        [
            render_metric_card("Ledger Books", str(len(ledgers)), "SUCCESS"),
            render_metric_card("Pending Entries", str(pending_entries), "OVERDUE" if pending_entries else "SUCCESS"),
            render_metric_card("Overdue Entries", str(overdue_entries), "OVERDUE" if overdue_entries else "OPEN"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(len(ledgers)), "tab_name": "Overview"},
            {"label": "Entries", "value": str(pending_entries), "tab_name": "Entries"},
            {"label": "Due/Overdue", "value": str(overdue_entries), "tab_name": "Due/Overdue"},
            {"label": "Settlements", "value": "Record", "tab_name": "Settlements"},
        ],
    )
    render_section_intro("Khata Snapshot", "Both marketplace and sourcing dues stay visible here without turning the product into a payment gateway. This is the finance surface that matters right now.")
    render_html(
        """
        <div class="mt-surface-note">
          This screen intentionally stays calmer than the rest of the shell: balances, due states, and reminders
          should be readable at a glance without heavy motion competing with the numbers.
        </div>
        """
    )
    overview_tab, entries_tab, due_tab, payments_tab = st.tabs(["Overview", "Entries", "Due/Overdue", "Settlements"])
    with overview_tab:
        if ledgers:
            render_3d_panel("".join(render_mobile_record_card(item) for item in ledgers[:4]), "Latest Ledger Relationships", tone="subtle")
            if user.role == "platform_admin":
                total_sale_amount = 0.0
                total_procurement_amount = 0.0
                for entry in app_context["governance_service"].list_supply_ledger_entries():
                    sale_amount = float(entry.get("manufacturer_bill_amount", entry.get("sale_amount", 0)) or 0)
                    procurement_amount = float(entry.get("amount_due_to_mahajan", entry.get("procurement_amount", 0)) or 0)
                    total_sale_amount += sale_amount
                    total_procurement_amount += procurement_amount
                margin = round(total_sale_amount - total_procurement_amount, 2)
                st.caption(f"Derived sourcing margin: sale {round(total_sale_amount, 2)} - procurement {round(total_procurement_amount, 2)} = {margin}")
        else:
            render_empty_state("No ledger relationships found yet.")
    with entries_tab:
        filtered_ledgers = render_filter_bar(page_key="ledger_entries", rows=ledgers, search_fields=["ledger_id", "party_a", "party_b"], status_field="status", date_field="updated_at")
        if filtered_ledgers:
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_ledgers), file_name="ledger.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_ledgers), file_name="ledger.json", mime="application/json", use_container_width=True)
            st.dataframe(filtered_ledgers, use_container_width=True)
        else:
            render_empty_state("No ledger relationships found yet.")
    with due_tab:
        overdue_rows = []
        if user.role in {"mahajan", "platform_admin"}:
            overdue_rows = [item for item in ledgers if item.get("status") in {"PENDING", "OVERDUE"}]
        else:
            for ledger in ledgers:
                for entry in ledger.get("entries", []):
                    if entry.get("status") in {"PENDING", "PARTIAL", "OVERDUE"}:
                        overdue_rows.append({"ledger_id": ledger.get("ledger_id"), **entry})
        if overdue_rows:
            st.dataframe(overdue_rows, use_container_width=True)
        else:
            render_empty_state("No due or overdue ledger entries right now.")
    with payments_tab:
        if user.role in {"mahajan", "platform_admin"}:
            st.info("Settlement visibility remains supervisory on this screen. No separate payment gateway workflow is assumed.")
            st.dataframe(ledgers, use_container_width=True)
            return
        payable_rows = []
        for ledger in ledgers:
            for entry in ledger.get("entries", []):
                payable_rows.append({"ledger_id": ledger.get("ledger_id"), **entry})
        if not payable_rows:
            render_empty_state("No ledger payments are available yet.")
        else:
            selected_entry = st.selectbox("Ledger Entry", [item["entry_id"] for item in payable_rows])
            amount = st.number_input("Payment Amount", min_value=0.0, step=1.0, value=0.0)
            note = st.text_input("Payment Note")
            if st.button("Add Payment", use_container_width=True, disabled=amount <= 0):
                selected = next(item for item in payable_rows if item["entry_id"] == selected_entry)
                app_context["ledger_service"].add_payment(user.manufacturer_code, selected["ledger_id"], selected_entry, amount, note)
                st.success("Ledger payment recorded.")
                st.rerun()
