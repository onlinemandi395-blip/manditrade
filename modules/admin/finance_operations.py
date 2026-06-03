from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from utils.page_ui import render_empty_state


def render_finance_operations_dashboard(app_context: dict) -> None:
    settlement_service = app_context["settlement_service"]
    invoice_service = app_context["invoice_service"]
    dispute_service = app_context["dispute_service"]
    render_platform_shell(
        title="Finance Operations",
        subtitle="Run settlements, invoices, overdue follow-up, dispute review, and commission visibility from one admin finance surface.",
        badges=["Transactions", "Invoices", "Disputes"],
        breadcrumbs=["Platform", "Finance", "Finance Operations"],
        primary_actions=["Refresh Overdue Detection"],
    )
    summary = settlement_service.summarize()
    rows = settlement_service.list_transactions()
    disputes = dispute_service.governance_service.list_disputes()
    invoices = invoice_service.list_invoices()
    render_kpi_cards(
        [
            {"label": "Transactions", "value": str(summary["transaction_count"]), "status": "OPEN"},
            {"label": "Outstanding", "value": str(summary["outstanding_balance"]), "status": "OVERDUE" if summary["outstanding_balance"] else "SUCCESS"},
            {"label": "Commission", "value": str(summary["commission_amount"]), "status": "SUCCESS"},
            {"label": "Disputes", "value": str(len([item for item in disputes if item.get("status") in {"OPEN", "UNDER_REVIEW"}])), "status": "WARNING"},
        ]
    )
    render_section_intro("Finance Control", "Marketplace, MandiPlace, supply, packaging, courier, and commission dues are tracked here in a compatibility-safe finance layer.")
    transactions_tab, invoices_tab, overdue_tab, disputes_tab, reconcile_tab = st.tabs(["Transactions", "Invoices", "Overdue", "Disputes", "Reconciliation"])
    with transactions_tab:
        filtered = render_data_grid(
            page_key="finance_transactions",
            rows=rows,
            search_fields=["financial_transaction_id", "related_order_id", "payer_id", "payee_id"],
            status_field="status",
            date_field="created_at",
            price_field="gross_amount",
        )
        if not filtered:
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
