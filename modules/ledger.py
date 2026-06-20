from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.ledger_service import LedgerService


def _render_revenue_summary_rows(rows: list[dict]) -> None:
    if not rows:
        return
    metric_cols = st.columns(4)
    metric_cols[0].metric("Accounts", sum(int(row.get("account_count", 0) or 0) for row in rows))
    metric_cols[1].metric("Platform Margin", f"Rs. {sum(float(row.get('platform_margin', 0) or 0) for row in rows):.2f}")
    metric_cols[2].metric("Packaging Revenue", f"Rs. {sum(float(row.get('packaging_revenue', 0) or 0) for row in rows):.2f}")
    metric_cols[3].metric("Shipping Revenue", f"Rs. {sum(float(row.get('shipping_revenue', 0) or 0) for row in rows):.2f}")


def render_ledger_page(data_service, notification_service, session_service, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    ledger_service = LedgerService(data_service)
    user = session_service.get_user()
    role = str(user.get("role", "")).strip().lower()
    email = str(user.get("email", "")).strip().lower()
    summaries = ledger_service.summarize_accounts(viewer_email=email, role=role)
    if role == "platform_admin":
        grouped_accounts = ledger_service.summarize_accounts_by_owner_role(role=role)
        admin_totals = ledger_service.summarize_admin_totals()
        _render_revenue_summary_rows(admin_totals)
        render_table(admin_totals, caption=t("ui.ledger_overview"))
        admin_tabs = st.tabs([t("ui.all_accounts"), t("ui.mahajans"), t("ui.other")])
        tab_rows = {
            t("ui.all_accounts"): summaries,
            t("ui.mahajans"): grouped_accounts.get("mahajan", []),
            t("ui.other"): grouped_accounts.get("other", []),
        }
        for tab, label in zip(admin_tabs, tab_rows.keys()):
            with tab:
                render_table(tab_rows[label], caption=label)
    else:
        render_table(summaries, caption=t("ui.my_ledger_accounts"))

    ledger_rows = data_service.get_collection_ref("ledger")
    if role == "platform_admin":
        owner_type_options = {
            t("ui.all"): "all",
            t("ui.mahajan"): "mahajan",
            t("ui.other"): "other",
        }
        owner_role_filter = st.selectbox(
            t("ui.owner_type"),
            options=list(owner_type_options.keys()),
            key="ledger_owner_role_filter",
        )
        filtered_summaries = summaries
        selected_filter = owner_type_options.get(owner_role_filter, "all")
        if selected_filter != "all":
            if selected_filter == "other":
                filtered_summaries = [
                    row for row in summaries if str(row.get("owner_role", "")).strip().lower() != "mahajan"
                ]
            else:
                filtered_summaries = [
                    row for row in summaries if str(row.get("owner_role", "")).strip().lower() == selected_filter
                ]
        selected_account = st.selectbox(
            t("ui.open_ledger_account"),
            options=[""] + [row.get("account_key", "") for row in filtered_summaries],
            format_func=lambda value: next(
                (
                    f"{row.get('owner_email', '')} | {str(row.get('owner_role', '')).title()} | Balance {row.get('balance', 0)}"
                    for row in filtered_summaries
                    if row.get("account_key", "") == value
                ),
                value,
            ),
            key="ledger_account_key",
        )
    else:
        selected_account = summaries[0].get("account_key", "") if summaries else ""

    if selected_account:
        account_rows = [row for row in ledger_rows if str(row.get("account_key", "")).strip() == selected_account]
        payable_rows = [row for row in account_rows if str(row.get("entry_type", "")).upper() == "PAYABLE_TO_OWNER"]
        settlement_rows = [row for row in account_rows if str(row.get("entry_type", "")).upper() == "PAYMENT_TO_OWNER"]
        margin_rows = [row for row in account_rows if str(row.get("entry_type", "")).upper() == "PLATFORM_MARGIN"]
        packaging_rows = [row for row in account_rows if str(row.get("entry_type", "")).upper() == "PACKAGING_FEE"]
        shipping_rows = [row for row in account_rows if str(row.get("entry_type", "")).upper() == "SHIPPING_FEE"]
        entry_tabs = st.tabs(
            [
                t("ui.ledger_entries"),
                t("ui.settlement_history"),
                t("ui.payable_history"),
                "Platform Margin",
                "Packaging",
                "Shipping",
            ]
        )
        with entry_tabs[0]:
            render_table(account_rows, caption=t("ui.ledger_entries"))
        with entry_tabs[1]:
            render_table(settlement_rows, caption=t("ui.settlement_history"))
        with entry_tabs[2]:
            render_table(payable_rows, caption=t("ui.payable_history"))
        with entry_tabs[3]:
            render_table(margin_rows, caption="Platform margin entries")
        with entry_tabs[4]:
            render_table(packaging_rows, caption="Packaging entries")
        with entry_tabs[5]:
            render_table(shipping_rows, caption="Shipping entries")
        if role == "platform_admin":
            owner = next((row for row in account_rows if str((row.get("party_owner") or {}).get("email", "")).strip()), {})
            owner_email = str((owner.get("party_owner") or {}).get("email", "")).strip().lower()
            owner_role = str((owner.get("party_owner") or {}).get("role", "")).strip().lower()
            st.markdown(f"### {t('ui.mark_partial_payment')}")
            payment_amount = st.number_input(t("ui.payment_amount"), min_value=0.0, step=1.0, key="ledger_payment_amount")
            payment_mode = st.selectbox(t("ui.payment_mode"), options=["UPI", "Bank", "Cash", "Credit"], key="ledger_payment_mode")
            payment_reference = st.text_input(t("ui.payment_reference"), key="ledger_payment_reference")
            payment_notes = st.text_area(t("ui.notes"), key="ledger_payment_notes")
            if st.button(t("ui.mark_payment"), use_container_width=True, key="ledger_mark_payment") and owner_email and payment_amount > 0:
                entry = ledger_service.create_payment_entry(
                    owner_email=owner_email,
                    owner_role=owner_role,
                    amount=payment_amount,
                    payment_mode=payment_mode,
                    payment_reference=payment_reference.strip(),
                    notes=payment_notes.strip(),
                    created_by=email,
                )
                data_service.persist_collection("ledger")
                notification_service.create_notification(
                    to_email=owner_email,
                    title="Payment marked",
                    message=f"Payment of {payment_amount} recorded for {owner_email}.",
                    event_type="PAYMENT_MARKED",
                    to_role=owner_role,
                    owner_email=owner_email,
                    source_entity="ledger",
                    source_id=entry.get("ledger_id", ""),
                    created_by=email,
                )
                notification_service.create_notification(
                    to_email=email,
                    title="Payment recorded",
                    message=f"Payment of {payment_amount} recorded.",
                    event_type="PAYMENT_MARKED",
                    to_role="platform_admin",
                    owner_email=owner_email,
                    source_entity="ledger",
                    source_id=entry.get("ledger_id", ""),
                    created_by=email,
                )
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success(t("ui.payment_recorded"))
                st.rerun()
