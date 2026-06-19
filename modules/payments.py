from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.payment_service import PaymentService
from services.qr_service import QRService


def render_payments_page(data_service, order_service, notification_service, session_service, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    payments = data_service.get_collection_ref("payments")
    orders = data_service.get_collection_ref("orders")
    qr_service = QRService()
    payment_service = PaymentService(data_service, data_service.cache_service)

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

    st.markdown("### Owner Managed Payments")
    payment_map = {row.get("payment_id", ""): row for row in pending_payments}
    search_text = st.text_input(
        t("ui.search_payment_reference"),
        key="payments_reference_search",
        help=t("ui.search_payment_reference_help"),
    )
    searchable_payments = pending_payments
    if str(search_text or "").strip():
        matched_payments = payment_service.find_payments_by_reference(search_text, pending_only=True)
        searchable_payments = [row for row in pending_payments if row in matched_payments]
        if searchable_payments:
            st.caption(f"{t('ui.search_results')}: {len(searchable_payments)}")
        else:
            st.warning(t("ui.no_matching_payment_found"))
            return
    payment_map = {row.get("payment_id", ""): row for row in searchable_payments}
    selected_payment_id = st.selectbox(
        t("ui.pending_payment"),
        options=[""] + list(payment_map.keys()),
        format_func=lambda value: (
            f"{payment_map[value].get('payment_reference', '')} | {value} | {payment_map[value].get('payer_email', '')} | {payment_map[value].get('amount_due', 0)}"
            if value in payment_map else value
        ),
        key="payments_pending_id",
    )
    payment = payment_map.get(selected_payment_id)
    if not payment:
        return
    if payment_service.ensure_payment_link_fields(payment):
        data_service.persist_collection("payments")
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
    financials = dict(related_order.get("financials", {}) or {})
    if financials:
        finance_cols = st.columns(4)
        finance_cols[0].metric("Merchandise", f"Rs. {float(financials.get('merchandise_total', 0) or 0):.2f}")
        finance_cols[1].metric("Packaging", f"Rs. {float(financials.get('packaging_charge', 0) or 0):.2f}")
        finance_cols[2].metric("Shipping", f"Rs. {float(financials.get('shipping_charge', 0) or 0):.2f}")
        finance_cols[3].metric("Owner Payable", f"Rs. {float(financials.get('owner_payable_amount', 0) or 0):.2f}")
    upi_link = str(payment.get("upi_link", "") or "").strip()
    st.code(upi_link)
    if upi_link:
        st.link_button(t("ui.pay_in_upi_app"), upi_link, use_container_width=True)
    qr_bytes = qr_service.build_qr_png_bytes(str(payment.get("qr_payload", "") or upi_link).strip())
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
            data=upi_link.encode("utf-8"),
            file_name=f"{payment.get('payment_reference', 'upi_payload')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    st.text_area(t("ui.share_copy_upi_link"), value=upi_link, height=100, key=f"payments_share_{selected_payment_id}")
    st.info("Payment confirmation now happens directly by the mahajan. Admin can monitor pending payments here.")
