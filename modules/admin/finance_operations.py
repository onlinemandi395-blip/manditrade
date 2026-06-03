from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state


def render_finance_operations_dashboard(app_context: dict) -> None:
    settlement_service = app_context["settlement_service"]
    invoice_service = app_context["invoice_service"]
    dispute_service = app_context["dispute_service"]
    render_page_header(
        "Finance Operations",
        "Run settlements, invoices, overdue follow-up, dispute review, and commission visibility from one admin finance surface.",
        ["Transactions", "Invoices", "Disputes"],
    )
    summary = settlement_service.summarize()
    rows = settlement_service.list_transactions()
    disputes = dispute_service.governance_service.list_disputes()
    invoices = invoice_service.list_invoices()
    render_metric_grid(
        [
            render_metric_card("Transactions", str(summary["transaction_count"]), "OPEN"),
            render_metric_card("Outstanding", str(summary["outstanding_balance"]), "OVERDUE" if summary["outstanding_balance"] else "SUCCESS"),
            render_metric_card("Commission", str(summary["commission_amount"]), "SUCCESS"),
            render_metric_card("Disputes", str(len([item for item in disputes if item.get("status") in {"OPEN", "UNDER_REVIEW"}])), "WARNING"),
        ]
    )
    render_section_intro("Finance Control", "Marketplace, MandiPlace, supply, packaging, courier, and commission dues are tracked here in a compatibility-safe finance layer.")
    transactions_tab, invoices_tab, overdue_tab, disputes_tab, reconcile_tab = st.tabs(["Transactions", "Invoices", "Overdue", "Disputes", "Reconciliation"])
    with transactions_tab:
        filtered = render_filter_bar(
            page_key="finance_transactions",
            rows=rows,
            search_fields=["financial_transaction_id", "related_order_id", "payer_id", "payee_id"],
            status_field="status",
            date_field="created_at",
            price_field="gross_amount",
        )
        if filtered:
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered), file_name="financial_transactions.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered), file_name="financial_transactions.json", mime="application/json", use_container_width=True)
            st.dataframe(filtered, use_container_width=True)
        else:
            render_empty_state("No financial transactions yet.")
    with invoices_tab:
        if invoices:
            st.dataframe(invoices, use_container_width=True)
        else:
            render_empty_state("No invoices generated yet.")
    with overdue_tab:
        overdue_rows = [item for item in rows if item.get("status") == "OVERDUE"]
        if overdue_rows:
            st.dataframe(overdue_rows, use_container_width=True)
        else:
            render_empty_state("No overdue settlements right now.")
    with disputes_tab:
        if disputes:
            st.dataframe(disputes, use_container_width=True)
        else:
            render_empty_state("No payment or settlement disputes yet.")
    with reconcile_tab:
        st.caption("Reconciliation is transaction-driven: payment proof, partials, and verified status update the same finance record.")
        if st.button("Refresh Overdue Detection", use_container_width=True):
            updated = settlement_service.mark_overdue_transactions()
            st.success(f"Updated {len(updated)} transactions.")
            st.rerun()
