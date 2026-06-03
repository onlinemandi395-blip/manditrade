from __future__ import annotations

import streamlit as st

from components.background_tasks_panel import render_background_tasks_panel
from components.bulk_actions import render_bulk_actions
from components.data_grid import render_data_grid
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from components.toast_manager import push_toast
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state


def render_finance_operations_dashboard(app_context: dict) -> None:
    settlement_service = app_context["settlement_service"]
    invoice_service = app_context["invoice_service"]
    dispute_service = app_context["dispute_service"]
    current_user = app_context["current_user"]
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
        else:
            selected_ids, triggered_action = render_bulk_actions(
                page_key="finance_transactions_bulk",
                rows=filtered,
                id_field="financial_transaction_id",
                action_options=[("export_csv", "Export Selected CSV"), ("export_json", "Export Selected JSON")],
                selection_label="Select transactions",
            )
            selected_rows = [row for row in filtered if row.get("financial_transaction_id") in selected_ids]
            if triggered_action and not selected_rows:
                push_toast("Select at least one transaction first.", tone="warning", title="Bulk Actions")
            elif selected_rows:
                if triggered_action == "export_csv":
                    st.download_button(
                        "Download Selected Transactions CSV",
                        export_rows_to_csv_bytes(selected_rows),
                        file_name="finance-transactions-selected.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="finance_transactions_download_csv",
                    )
                elif triggered_action == "export_json":
                    st.download_button(
                        "Download Selected Transactions JSON",
                        export_rows_to_json_bytes(selected_rows),
                        file_name="finance-transactions-selected.json",
                        mime="application/json",
                        use_container_width=True,
                        key="finance_transactions_download_json",
                    )
    with invoices_tab:
        if invoices:
            st.dataframe(invoices, use_container_width=True)
        else:
            render_empty_state("No invoices generated yet.")
    with overdue_tab:
        overdue_rows = [item for item in rows if item.get("status") == "OVERDUE"]
        if overdue_rows:
            st.dataframe(overdue_rows, use_container_width=True)
            selected_ids, triggered_action = render_bulk_actions(
                page_key="finance_overdue_bulk",
                rows=overdue_rows,
                id_field="financial_transaction_id",
                action_options=[("export_csv", "Export Overdue CSV")],
                selection_label="Select overdue transactions",
            )
            selected_rows = [row for row in overdue_rows if row.get("financial_transaction_id") in selected_ids]
            if triggered_action == "export_csv" and selected_rows:
                st.download_button(
                    "Download Selected Overdue CSV",
                    export_rows_to_csv_bytes(selected_rows),
                    file_name="finance-overdue-selected.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="finance_overdue_download_csv",
                )
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
            task = app_context["recovery_action_service"].execute(
                "refresh_overdue_detection",
                app_context,
                actor_role=getattr(current_user, "role", ""),
                actor_id=getattr(current_user, "email", "platform_admin"),
            )
            push_toast(f"Overdue detection queued with status {task.get('status', 'UNKNOWN')}.", tone="success", title="Recovery")
            st.rerun()
        render_background_tasks_panel(app_context, page_key="finance_background_tasks", limit=10)
