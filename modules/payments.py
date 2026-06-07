from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.qr_service import QRService


def render_payments_page(data_service, order_service, notification_service, session_service) -> None:
    payments = data_service.get_collection_ref("payments")
    orders = data_service.get_collection_ref("orders")
    qr_service = QRService()

    tabs = st.tabs(["Pending Verification", "Verified Payments", "All Payments"])
    with tabs[0]:
        pending_payments = [row for row in payments if str(row.get("status", "")).upper() == "PAYMENT_PENDING"]
        render_table(pending_payments, caption="Pending Verification")
    with tabs[1]:
        verified_payments = [row for row in payments if str(row.get("status", "")).upper() == "PAYMENT_VERIFIED"]
        render_table(verified_payments, caption="Verified Payments")
    with tabs[2]:
        render_table(payments, caption="All Payments")

    pending_payments = [row for row in payments if str(row.get("status", "")).upper() == "PAYMENT_PENDING"]
    if not pending_payments:
        st.success("No pending payments.")
        return

    st.markdown("### Verify Payment")
    payment_map = {row.get("payment_id", ""): row for row in pending_payments}
    selected_payment_id = st.selectbox(
        "Pending Payment",
        options=[""] + list(payment_map.keys()),
        format_func=lambda value: (
            f"{value} | {payment_map[value].get('payer_email', '')} | {payment_map[value].get('amount_due', 0)}"
            if value in payment_map else value
        ),
        key="payments_pending_id",
    )
    payment = payment_map.get(selected_payment_id)
    if not payment:
        return
    related_order = next((row for row in orders if str(row.get("payment_id", "")).strip() == str(selected_payment_id).strip()), {})
    detail_cols = st.columns(4)
    detail_cols[0].metric("Order", related_order.get("order_id", ""))
    detail_cols[1].metric("Buyer / Payer", payment.get("payer_email", ""))
    detail_cols[2].metric("Amount Due", payment.get("amount_due", 0))
    detail_cols[3].metric("Payment Ref", payment.get("payment_reference", ""))
    st.caption(f"Owner: {related_order.get('owner_email', '')} | Product: {related_order.get('product_name', '')}")
    st.code(payment.get("upi_link", ""))
    qr_bytes = qr_service.build_qr_png_bytes(payment.get("qr_payload", "") or payment.get("upi_link", ""))
    if qr_bytes:
        st.image(qr_bytes, caption="Scan QR to pay", width=220)
        qr_cols = st.columns(2)
        qr_cols[0].download_button(
            "Download QR PNG",
            data=qr_bytes,
            file_name=f"{payment.get('payment_reference', 'payment_qr')}.png",
            mime="image/png",
            use_container_width=True,
        )
        qr_cols[1].download_button(
            "Download UPI Payload",
            data=(payment.get("upi_link", "") or "").encode("utf-8"),
            file_name=f"{payment.get('payment_reference', 'upi_payload')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    st.text_area("Share / Copy UPI Link", value=payment.get("upi_link", ""), height=100, key=f"payments_share_{selected_payment_id}")
    amount_received = st.number_input("Amount Received", min_value=0.0, step=1.0, value=float(payment.get("amount_due", 0) or 0), key="payments_amount_received")
    transaction_reference = st.text_input("Transaction Reference", key="payments_transaction_reference")
    notes = st.text_area("Notes", key="payments_notes")
    if st.button("Verify Payment", use_container_width=True, key="payments_verify_button"):
        result = order_service.verify_payment(
            order_id=related_order.get("order_id", ""),
            amount_received=amount_received,
            transaction_reference=transaction_reference,
            notes=notes,
            verified_by=session_service.get_user().get("email", ""),
        )
        data_service.persist_collection("payments")
        data_service.persist_collection("orders")
        data_service.persist_collection("notifications")
        data_service.persist_collection("gmail_queue")
        st.success(f"Payment verified for order {result['order'].get('order_id', '')}.")
        st.rerun()
