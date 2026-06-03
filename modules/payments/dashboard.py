from __future__ import annotations

import streamlit as st

from components.platform_shell import render_platform_shell
from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.kpi_cards import render_kpi_cards
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state, render_metric_button_row


def render_payments_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    settlement_service = app_context.get("settlement_service")
    dispute_service = app_context.get("dispute_service")
    page_key = "payments"
    render_platform_shell(
        title="Payments",
        subtitle="Track direct seller and supplier payments and keep follow-up communication organised from one place.",
        badges=["Payment Follow-Up", "Email Reminders"],
        role=user.role.replace("_", " ").title() if user else None,
        breadcrumbs=["Workspace", "Finance", "Payments"],
    )
    if not user:
        st.info("Sign in required.")
        return
    manufacturer_code = user.manufacturer_code or ""
    reminder_ready = bool(manufacturer_code and user.role in {"manufacturer", "admin_as_manufacturer"})
    render_kpi_cards(
        [
            {"label": "Reminder Channel", "value": "Email", "status": "OPEN"},
            {"label": "Trigger", "value": "Send Now" if reminder_ready else "View Only", "status": "SUCCESS"},
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
        if settlement_service and user.role in {"manufacturer", "mahajan", "public_buyer"}:
            owner_id = user.manufacturer_code if user.role == "manufacturer" else user.email
            summary = settlement_service.summarize(role=user.role, owner_id=owner_id)
            st.caption(f"Tracked transactions: {summary['transaction_count']} | Outstanding: {summary['outstanding_balance']} | Commission-linked: {summary['commission_amount']}")
    with pending_tab:
        if user.role == "mahajan":
            if settlement_service:
                mahajan = app_context["governance_service"].get_mahajan_by_email(user.email) or {}
                tx_rows = settlement_service.list_transactions(role="mahajan", owner_id=mahajan.get("mahajan_id", ""))
                if tx_rows:
                    st.dataframe(tx_rows, use_container_width=True)
                    return
            mahajan = app_context["governance_service"].get_mahajan_by_email(user.email)
            entries = [
                item
                for item in app_context["governance_service"].list_supply_ledger_entries()
                if item.get("mahajan_id") == (mahajan or {}).get("mahajan_id")
            ]
            filtered_entries = render_filter_bar(page_key="payments_mahajan", rows=entries, search_fields=["entry_id", "mandi_order_id", "mahajan_id"], status_field="status", date_field="created_at", price_field="amount_due_to_mahajan")
            if filtered_entries:
                st.dataframe(filtered_entries, use_container_width=True)
            else:
                render_empty_state("No supplier payments are pending.")
            return
        if user.role == "platform_admin":
            if settlement_service:
                finance_rows = settlement_service.list_transactions()
                filtered_rows = render_filter_bar(page_key="payments_admin_finance", rows=finance_rows, search_fields=["financial_transaction_id", "related_order_id", "payer_id", "payee_id"], status_field="status", date_field="created_at", price_field="gross_amount")
                if filtered_rows:
                    csv_col, json_col = st.columns(2)
                    csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_rows), file_name="finance_transactions.csv", mime="text/csv", use_container_width=True)
                    json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_rows), file_name="finance_transactions.json", mime="application/json", use_container_width=True)
                    st.dataframe(filtered_rows, use_container_width=True)
                    return
            entries = app_context["governance_service"].list_supply_ledger_entries()
            filtered_entries = render_filter_bar(page_key="payments_admin", rows=entries, search_fields=["entry_id", "mandi_order_id", "mahajan_id", "manufacturer_id"], status_field="status", date_field="created_at", price_field="amount_due_to_mahajan")
            if filtered_entries:
                csv_col, json_col = st.columns(2)
                csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_entries), file_name="payments.csv", mime="text/csv", use_container_width=True)
                json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_entries), file_name="payments.json", mime="application/json", use_container_width=True)
                st.dataframe(filtered_entries, use_container_width=True)
            else:
                render_empty_state("No supplier payments are pending.")
            return
        if manufacturer_code:
            if settlement_service:
                finance_rows = settlement_service.list_transactions(role="manufacturer", owner_id=manufacturer_code)
                if finance_rows:
                    st.dataframe(finance_rows, use_container_width=True)
                else:
                    st.info("Pending verification and reminder-sensitive items are handled through ledger and order workflows.")
            else:
                st.info("Pending verification and reminder-sensitive items are handled through ledger and order workflows.")
        else:
            render_empty_state("No manufacturer-linked pending payment workflow is available for this session.")
        if reminder_ready and st.button("Send Ledger Reminders Now", use_container_width=True):
            triggered = app_context["ledger_reminder_service"].run_for_manufacturer(user.manufacturer_code, user.email)
            st.success(f"Triggered {triggered} reminder emails.")
    with verified_tab:
        if settlement_service:
            if user.role == "platform_admin":
                verified_rows = [item for item in settlement_service.list_transactions() if item.get("status") == "PAID"]
            else:
                owner_id = user.manufacturer_code if user.role == "manufacturer" else user.email
                verified_rows = [item for item in settlement_service.list_transactions(role=user.role, owner_id=owner_id) if item.get("status") == "PAID"]
            if verified_rows:
                st.dataframe(verified_rows, use_container_width=True)
            else:
                render_empty_state("No verified finance transactions yet.")
        else:
            render_empty_state("Verified payment history is surfaced in role-specific order and ledger views.")
    with disputed_tab:
        disputes = dispute_service.governance_service.list_disputes() if dispute_service else []
        if disputes:
            st.dataframe(disputes, use_container_width=True)
        else:
            render_empty_state("No payment disputes are open right now.")
