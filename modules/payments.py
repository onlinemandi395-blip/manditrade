from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.qr_service import QRService


def render_payments_page(data_service, order_service, notification_service, session_service, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    payments = data_service.get_collection_ref("payments")
    orders = data_service.get_collection_ref("orders")
    qr_service = QRService()

    tabs = st.tabs([t("ui.pending_verification"), t("ui.verified_payments"), t("ui.all_payments")])
    with tabs[0]:
        pending_payments = [row for row in payments if str(row.get("payment_status", row.get("status", ""))).upper() in {"PENDING", "PAYMENT_PENDING"}]
        render_table(pending_payments, caption=t("ui.pending_verification"))
    with tabs[1]:
        verified_payments = [row for row in payments if str(row.get("payment_status", row.get("status", ""))).upper() in {"VERIFIED", "PAYMENT_VERIFIED"}]
        render_table(verified_payments, caption=t("ui.verified_payments"))
    with tabs[2]:
        render_table(payments, caption=t("ui.all_payments"))

    pending_payments = [row for row in payments if str(row.get("payment_status", row.get("status", ""))).upper() in {"PENDING", "PAYMENT_PENDING"}]
    if not pending_payments:
        st.success(t("ui.no_pending_payments"))
        return

    st.markdown(f"### {t('ui.verify_payment')}")
    payment_map = {row.get("payment_id", ""): row for row in pending_payments}
    selected_payment_id = st.selectbox(
        t("ui.pending_payment"),
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
    detail_cols[0].metric(t("module.orders.title"), related_order.get("order_id", ""))
    detail_cols[1].metric(t("ui.buyer_payer"), payment.get("payer_email", ""))
    detail_cols[2].metric(t("ui.amount_due"), payment.get("amount_payable", payment.get("amount_due", 0)))
    detail_cols[3].metric(t("ui.payment_reference"), payment.get("payment_reference", ""))
    st.caption(
        f"{t('ui.owner')}: {related_order.get('owner_email', '')} | "
        f"{t('ui.product')}: {related_order.get('product_name', '')} | "
        f"{t('ui.source')}: {related_order.get('source_channel', '')}"
    )
    st.code(payment.get("upi_link", ""))
    qr_bytes = qr_service.build_qr_png_bytes(payment.get("qr_payload", "") or payment.get("upi_link", ""))
    if qr_bytes:
        st.image(qr_bytes, caption=t("ui.scan_qr_to_pay"), width=220)
        qr_cols = st.columns(2)
        qr_cols[0].download_button(
            t("ui.download_qr_png"),
            data=qr_bytes,
            file_name=f"{payment.get('payment_reference', 'payment_qr')}.png",
            mime="image/png",
            use_container_width=True,
        )
        qr_cols[1].download_button(
            t("ui.download_upi_payload"),
            data=(payment.get("upi_link", "") or "").encode("utf-8"),
            file_name=f"{payment.get('payment_reference', 'upi_payload')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    st.text_area(t("ui.share_copy_upi_link"), value=payment.get("upi_link", ""), height=100, key=f"payments_share_{selected_payment_id}")
    amount_received = st.number_input(t("ui.amount_received"), min_value=0.0, step=1.0, value=float(payment.get("amount_payable", payment.get("amount_due", 0)) or 0), key="payments_amount_received")
    transaction_reference = st.text_input(t("ui.transaction_reference"), key="payments_transaction_reference")
    notes = st.text_area(t("ui.notes"), key="payments_notes")
    if st.button(t("ui.verify_payment"), use_container_width=True, key="payments_verify_button"):
        result = order_service.verify_payment(
            order_id=related_order.get("order_id", ""),
            amount_received=amount_received,
            transaction_reference=transaction_reference,
            notes=notes,
            verified_by=session_service.get_user().get("email", ""),
        )
        data_service.persist_collection("payments")
        order_service.persist_order_storage(related_order)
        data_service.persist_collection("notifications")
        data_service.persist_collection("gmail_queue")
        st.success(f"{t('ui.payment_verified_for_order')} {result['order'].get('order_id', '')}.")
        st.rerun()
