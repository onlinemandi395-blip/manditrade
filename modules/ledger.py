from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.ledger_service import LedgerService


def render_ledger_page(data_service, notification_service, session_service) -> None:
    ledger_service = LedgerService(data_service)
    user = session_service.get_user()
    role = str(user.get("role", "")).strip().lower()
    email = str(user.get("email", "")).strip().lower()
    summaries = ledger_service.summarize_accounts(viewer_email=email, role=role)
    render_table(summaries, caption="Ledger Accounts")

    ledger_rows = data_service.get_collection_ref("ledger")
    if role == "platform_admin":
        selected_account = st.selectbox(
            "Open Ledger Account",
            options=[""] + [row.get("account_key", "") for row in summaries],
            key="ledger_account_key",
        )
    else:
        selected_account = summaries[0].get("account_key", "") if summaries else ""

    if selected_account:
        account_rows = [row for row in ledger_rows if str(row.get("account_key", "")).strip() == selected_account]
        render_table(account_rows, caption="Ledger Entries")
        if role == "platform_admin":
            owner = next((row for row in account_rows if str((row.get("party_owner") or {}).get("email", "")).strip()), {})
            owner_email = str((owner.get("party_owner") or {}).get("email", "")).strip().lower()
            owner_role = str((owner.get("party_owner") or {}).get("role", "")).strip().lower()
            st.markdown("### Mark Partial Payment")
            payment_amount = st.number_input("Payment Amount", min_value=0.0, step=1.0, key="ledger_payment_amount")
            payment_mode = st.selectbox("Payment Mode", options=["UPI", "Bank", "Cash", "Credit"], key="ledger_payment_mode")
            payment_reference = st.text_input("Payment Reference", key="ledger_payment_reference")
            payment_notes = st.text_area("Notes", key="ledger_payment_notes")
            if st.button("Mark Payment", use_container_width=True, key="ledger_mark_payment") and owner_email and payment_amount > 0:
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
                    notification_type="PAYMENT_MARKED",
                    title="Payment marked",
                    message=f"Payment of {payment_amount} recorded for {owner_email}.",
                    metadata={"to_email": owner_email, "ledger_id": entry.get("ledger_id", "")},
                )
                notification_service.create_notification(
                    notification_type="PAYMENT_MARKED",
                    title="Payment recorded",
                    message=f"Payment of {payment_amount} recorded.",
                    metadata={"to_email": email, "ledger_id": entry.get("ledger_id", "")},
                )
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success("Payment recorded.")
                st.rerun()
