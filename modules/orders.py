from __future__ import annotations

import streamlit as st

from components.empty_state import render_empty_state
from components.table_renderer import render_table
from components.html_renderer import render_template
from services.document_service import DocumentService
from services.payment_service import PaymentService
from services.qr_service import QRService


def _render_order_financial_summary(selected_order: dict, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    financials = dict(selected_order.get("financials", {}) or {})
    service_config = dict(selected_order.get("service_config", {}) or {})
    cols = st.columns(4)
    cols[0].metric("Merchandise", f"Rs. {float(financials.get('merchandise_total', selected_order.get('merchandise_total', 0)) or 0):.2f}")
    cols[1].metric("Platform Margin", f"Rs. {float(financials.get('platform_margin', selected_order.get('admin_margin', 0)) or 0):.2f}")
    cols[2].metric("Packaging", f"Rs. {float(financials.get('packaging_charge', 0) or 0):.2f}")
    cols[3].metric("Shipping", f"Rs. {float(financials.get('shipping_charge', 0) or 0):.2f}")
    secondary_cols = st.columns(4)
    secondary_cols[0].metric("Owner Payable", f"Rs. {float(financials.get('owner_payable_amount', ((selected_order.get('internal') or {}).get('owner_payable_amount', 0))) or 0):.2f}")
    secondary_cols[1].metric(t("ui.amount"), f"Rs. {float(financials.get('grand_total', selected_order.get('total_amount', 0)) or 0):.2f}")
    secondary_cols[2].metric("Packaging Mode", str(service_config.get("packaging_mode", "owner") or "owner").title())
    secondary_cols[3].metric("Shipping Mode", str(service_config.get("shipping_mode", "owner") or "owner").title())
    if str(service_config.get("delivery_notes", "")).strip():
        st.caption(f"Fulfillment note: {service_config.get('delivery_notes', '')}")


def _render_order_items(selected_order: dict) -> None:
    items = [dict(item or {}) for item in (selected_order.get("items", []) or [])]
    if not items:
        return
    render_table(items, caption="Order line items")


def _render_order_address(selected_order: dict) -> None:
    delivery_address = dict(selected_order.get("delivery_address", {}) or {})
    if not any(str(value or "").strip() for value in delivery_address.values()):
        return
    address_parts = [
        str(delivery_address.get("address_line_1", "")).strip(),
        str(delivery_address.get("address_line_2", "")).strip(),
        str(delivery_address.get("city", "")).strip(),
        str(delivery_address.get("state", "")).strip(),
        str(delivery_address.get("pin_code", "")).strip(),
    ]
    address_text = ", ".join([part for part in address_parts if part])
    if str(delivery_address.get("landmark", "")).strip():
        address_text = f"{address_text} | Landmark: {delivery_address.get('landmark', '')}" if address_text else f"Landmark: {delivery_address.get('landmark', '')}"
    if address_text:
        st.caption(f"Delivery address: {address_text}")


def _tabs_for_role(role: str, current_user_email: str = "", translator=None) -> dict[str, callable]:
    t = translator.t if translator else (lambda key: key)
    active_statuses = {
        "PAYMENT_PENDING",
        "PAYMENT_VERIFIED",
        "OWNER_ACCEPTED",
        "READY_FOR_PICKUP",
        "PICKUP_ASSIGNED",
        "PICKED_UP",
        "IN_TRANSIT",
    }
    completed_statuses = {"COMPLETED", "DELIVERED", "CLOSED"}
    if role == "platform_admin":
        return {
            t("ui.all_orders"): lambda rows: rows,
            t("module.marketplace.title"): lambda rows: [row for row in rows if row.get("source_channel") == "marketplace"],
            t("module.manditrade.title"): lambda rows: [row for row in rows if row.get("source_channel") == "manditrade"],
            t("ui.payment_pending"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "PAYMENT_PENDING"],
            t("ui.payment_verified"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "PAYMENT_VERIFIED"],
            t("ui.in_progress"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() in active_statuses],
            t("ui.completed"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() in completed_statuses],
        }
    if role == "merchant":
        return {
            t("ui.payment_pending"): lambda rows: [
                row
                for row in rows
                if str(row.get("status", "")).upper() == "PAYMENT_PENDING"
                and str(row.get("owner_email", "")).strip().lower() == current_user_email
            ],
            t("ui.payment_verified"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "OWNER_ACCEPTED"],
            t("ui.accepted"): lambda rows: [row for row in rows if str(row.get("owner_status", "")).upper() == "ACCEPTED"],
            t("ui.ready_assigned"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() in {"READY_FOR_PICKUP", "PICKUP_ASSIGNED", "PICKED_UP"}],
            t("ui.in_progress"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() in {"IN_TRANSIT"}],
            t("ui.completed"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() in completed_statuses],
        }
    return {
        t("ui.my_orders"): lambda rows: rows,
    }


def _can_pay_order(selected_order: dict, role: str, current_user_email: str) -> bool:
    normalized_email = str(current_user_email or "").strip().lower()
    return (
        role in {"public_buyer", "client_buyer", "merchant"}
        and str(selected_order.get("status", "")).upper() == "PAYMENT_PENDING"
        and normalized_email in {
            str(selected_order.get("buyer_email", "")).strip().lower(),
            str(selected_order.get("requester_email", "")).strip().lower(),
            str(((selected_order.get("buyer") or {}).get("email", ""))).strip().lower(),
            str(((selected_order.get("requester") or {}).get("email", ""))).strip().lower(),
        }
    )


def _render_payment_panel(payment_record: dict, *, payment_service: PaymentService | None = None, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    qr_service = QRService()
    if payment_service is not None:
        payment_service.ensure_payment_link_fields(payment_record)
    upi_link = str(payment_record.get("upi_link", "") or "").strip()
    qr_payload = str(payment_record.get("qr_payload", "") or upi_link).strip()
    st.markdown(f"#### {t('ui.complete_payment')}")
    st.write(f"{t('ui.order_reference')}: {payment_record.get('payment_reference', '')}")
    st.write(f"{t('ui.amount')}: Rs. {payment_record.get('amount_payable', payment_record.get('amount_due', 0))}")
    st.write(f"{t('ui.payment_method')}: UPI")
    qr_bytes = qr_service.build_qr_png_bytes(qr_payload)
    if qr_bytes:
        st.image(qr_bytes, width=220)
    else:
        st.warning(t("ui.qr_not_generated"))
    if upi_link:
        st.link_button(t("ui.pay_in_upi_app"), upi_link, use_container_width=True)
    st.code(upi_link)
    st.caption(t("ui.pay_using_qr_note"))
    if str(payment_record.get("receiver_payee_name", "")).strip():
        st.caption(f"Payee: {payment_record.get('receiver_payee_name', '')}")
    if str(payment_record.get("receiver_upi_id", "")).strip():
        st.caption(f"UPI ID: {payment_record.get('receiver_upi_id', '')}")
    if str(payment_record.get("receiver_gst_number", "")).strip():
        st.caption(f"GST: {payment_record.get('receiver_gst_number', '')}")
    st.info("Payment will be confirmed by the product owner.")


def _render_buyer_status_tracker(selected_order: dict, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    stages = [
        "PAYMENT_PENDING",
        "PAYMENT_VERIFIED",
        "OWNER_ACCEPTED",
        "READY_FOR_PICKUP",
        "PICKUP_ASSIGNED",
        "PICKED_UP",
        "IN_TRANSIT",
        "COMPLETED",
    ]
    current_status = str(selected_order.get("status", "")).upper()
    cols = st.columns(len(stages))
    current_index = stages.index(current_status) if current_status in stages else -1
    for index, (col, stage) in enumerate(zip(cols, stages)):
        with col:
            if index < current_index:
                st.success(t(f"status.{stage.lower()}"))
            elif index == current_index:
                st.info(t(f"status.{stage.lower()}"))
            else:
                st.caption(t(f"status.{stage.lower()}"))


def _invoice_ready(order: dict) -> bool:
    payment_status = str(order.get("payment_status", order.get("status", "")) or "").strip().upper()
    return payment_status in {"VERIFIED", "PAYMENT_VERIFIED"} or str(order.get("status", "")).strip().upper() == "PAYMENT_VERIFIED"


def _render_order_cards(
    filtered_rows: list[dict],
    *,
    products_by_id: dict[str, dict],
    media_service=None,
    key_prefix: str,
    translator=None,
) -> str:
    t = translator.t if translator else (lambda key: key)
    no_orders_text = "No orders found."
    invoice_ready_text = "Invoice ready for download."
    invoice_after_payment_text = "Invoice will be available after the owner confirms the payment."
    if not filtered_rows:
        render_empty_state(no_orders_text)
        return ""
    selected_order_id = str(st.session_state.get(f"order_card_selected_{key_prefix}", "") or "").strip()
    for row_start in range(0, len(filtered_rows), 4):
        row_orders = filtered_rows[row_start:row_start + 4]
        columns = st.columns(4, gap="small")
        for column_index, column in enumerate(columns):
            if column_index >= len(row_orders):
                continue
            order = row_orders[column_index]
            product = dict(products_by_id.get(str(order.get("product_id", "")).strip(), {}) or {})
            images = [dict(image or {}) for image in (product.get("images", []) or [])]
            primary_image = next((image for image in images if image.get("is_primary")), images[0] if images else {})
            with column:
                with st.container(border=True):
                    renderable = media_service.get_renderable_image(primary_image) if media_service and primary_image else {"render_mode": "placeholder"}
                    if renderable.get("render_mode") == "bytes" and renderable.get("bytes"):
                        st.image(renderable["bytes"], use_container_width=True)
                    elif renderable.get("render_mode") == "url" and renderable.get("url"):
                        st.image(renderable["url"], use_container_width=True)
                    else:
                        render_template("product_card_media_placeholder.html", label="No Image")
                    st.markdown(f"**{order.get('product_name', order.get('order_id', 'Order'))}**")
                    st.caption(f"{order.get('order_id', '')} | {order.get('source_channel', '').upper()}")
                    st.caption(
                        f"{t('field.quantity')}: {float(order.get('quantity', 0) or 0):g} | "
                        f"{t('ui.amount')}: Rs. {float(order.get('total_amount', 0) or 0):g}"
                    )
                    st.caption(f"{t('field.status')}: {order.get('status', '')}")
                    if _invoice_ready(order):
                        st.caption(invoice_ready_text)
                    else:
                        st.caption(invoice_after_payment_text)
                    if st.button(
                        t("ui.order_detail"),
                        key=f"order_card_open_{key_prefix}_{order.get('order_id', '')}",
                        use_container_width=True,
                    ):
                        st.session_state[f"order_card_selected_{key_prefix}"] = str(order.get("order_id", "")).strip()
                        st.rerun()
    return selected_order_id


def render_orders_page(rows: list[dict], role: str, *, data_service=None, order_service=None, notification_service=None, session_service=None, translator=None, media_service=None) -> None:
    t = translator.t if translator else (lambda key: key)
    document_service = DocumentService()
    current_user_email = str(((session_service.get_user() if session_service else {}) or {}).get("email", "")).strip().lower()
    tab_map = _tabs_for_role(role, current_user_email, translator)
    tabs = st.tabs(list(tab_map.keys()))
    for tab, (label, filter_fn) in zip(tabs, tab_map.items()):
        with tab:
            key_prefix = f"{role}_{label}_{str(label).strip().lower().replace(' ', '_')}"
            filtered_rows = filter_fn(rows)
            if not filtered_rows:
                if role in {"public_buyer", "client_buyer"}:
                    render_empty_state("No orders found.")
                else:
                    render_table(filtered_rows, caption=label)
                continue
            products_by_id = {}
            if data_service is not None:
                products_by_id = {
                    str(row.get("product_id", "")).strip(): row
                    for row in data_service.get_collection_ref("products")
                    if str(row.get("product_id", "")).strip()
                }
            if role in {"public_buyer", "client_buyer"}:
                selected_order_id = _render_order_cards(
                    filtered_rows,
                    products_by_id=products_by_id,
                    media_service=media_service,
                    key_prefix=key_prefix,
                    translator=translator,
                )
            else:
                render_table(filtered_rows, caption=label)
                selected_order_id = ""
            order_map = {str(row.get("order_id", "")).strip(): row for row in filtered_rows if str(row.get("order_id", "")).strip()}
            if role not in {"public_buyer", "client_buyer"}:
                selected_order_id = st.selectbox(
                    f"{label} {t('ui.order_detail')}",
                    options=[""] + list(order_map.keys()),
                    key=f"order_detail_{key_prefix}",
                )
            selected_order = order_map.get(selected_order_id)
            if not selected_order:
                continue
            st.markdown(f"#### {t('ui.order_detail')}")
            meta_cols = st.columns(4)
            meta_cols[0].metric(t("field.status"), selected_order.get("status", ""))
            meta_cols[1].metric(t("module.payments.title"), selected_order.get("payment_reference", ""))
            meta_cols[2].metric(t("ui.owner_status"), selected_order.get("owner_status", ""))
            meta_cols[3].metric(t("ui.delivery_status"), selected_order.get("delivery_status", ""))
            st.caption(
                f"{t('ui.product')}: {selected_order.get('product_name', '')} | "
                f"{t('field.quantity')}: {selected_order.get('quantity', 0)} | "
                f"{t('ui.amount')}: {selected_order.get('total_amount', 0)}"
            )
            _render_order_financial_summary(selected_order, translator)
            _render_order_address(selected_order)
            _render_order_items(selected_order)
            if _invoice_ready(selected_order):
                invoice_html = document_service.build_invoice_html(selected_order)
                st.download_button(
                    t("ui.download_invoice"),
                    data=invoice_html.encode("utf-8"),
                    file_name=f"{selected_order_id}_invoice.html",
                    mime="text/html",
                    key=f"download_invoice_{key_prefix}_{selected_order_id}",
                )
            else:
                st.info("Invoice will be available after the owner confirms the payment.")
            if data_service is not None:
                shipment_rows = data_service.get_collection_ref("shipments")
                related_shipment = next((row for row in shipment_rows if str(row.get("order_id", "")).strip() == selected_order_id), {})
                if related_shipment:
                    delivery_slip_html = document_service.build_delivery_slip_html(selected_order, related_shipment)
                    st.download_button(
                        t("ui.download_delivery_slip"),
                        data=delivery_slip_html.encode("utf-8"),
                        file_name=f"{selected_order_id}_delivery_slip.html",
                        mime="text/html",
                        key=f"download_delivery_slip_{key_prefix}_{selected_order_id}",
                    )
            if role == "platform_admin":
                st.info(
                    f"Next action: admin_status={selected_order.get('admin_status', '')}, "
                    f"payment_id={selected_order.get('payment_id', '')}"
                )
                st.caption("Shipment execution and pickup assignment are handled directly by the merchant.")
                if data_service is not None and order_service is not None and session_service is not None:
                    st.markdown(f"##### {t('ui.admin_cleanup')}")
                    if st.button(t("ui.delete_order"), use_container_width=True, type="primary", key=f"delete_order_{key_prefix}_{selected_order_id}"):
                        try:
                            result = order_service.delete_order_for_admin(
                                order_id=selected_order_id,
                                deleted_by=session_service.get_user().get("email", ""),
                            )
                            data_service.persist_collection(result.get("collection_name", ""))
                            data_service.persist_collection("payments")
                            data_service.persist_collection("shipments")
                            data_service.persist_collection("ledger")
                            data_service.persist_collection("notifications")
                            data_service.persist_collection("gmail_queue")
                            st.success(
                                f"Order {result.get('order_id', '')} deleted. "
                                f"Related shipments removed: {len(result.get('shipment_ids', []))}."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Delete Order failed: {exc}")
            if role in {"public_buyer", "client_buyer"}:
                st.markdown(f"#### {t('ui.order_status_tracker')}")
                _render_buyer_status_tracker(selected_order, translator)
                otp_status = str(selected_order.get("otp_status", "")).upper()
                if otp_status in {"GENERATED", "VERIFIED"} and str(selected_order.get("delivery_otp", "")).strip():
                    st.success(f"{t('ui.delivery_otp')}: {selected_order.get('delivery_otp', '')}")
                else:
                    st.caption(t("ui.delivery_otp_will_appear"))
            if _can_pay_order(selected_order, role, current_user_email) and data_service is not None:
                payment_rows = data_service.get_collection_ref("payments")
                payment_record = next(
                    (row for row in payment_rows if str(row.get("payment_id", "")).strip() == str(selected_order.get("payment_id", "")).strip()),
                    {},
                )
                if payment_record:
                    payment_service = PaymentService(data_service, data_service.cache_service)
                    payment_link_changed = payment_service.ensure_payment_link_fields(payment_record)
                    if payment_link_changed:
                        data_service.persist_collection("payments")
                    _render_payment_panel(payment_record, payment_service=payment_service, translator=translator)
            if (
                role == "merchant"
                and data_service is not None
                and order_service is not None
                and str(selected_order.get("owner_email", "")).strip().lower() == current_user_email
                and str(selected_order.get("status", "")).upper() == "PAYMENT_PENDING"
            ):
                st.markdown("##### Confirm Payment and Order")
                owner_cols = st.columns(3)
                amount_received = owner_cols[0].number_input(
                    "Amount Received",
                    min_value=0.0,
                    step=1.0,
                    value=float(selected_order.get("total_amount", 0) or 0),
                    key=f"owner_verify_amount_{key_prefix}_{selected_order_id}",
                )
                transaction_reference = owner_cols[1].text_input(
                    "Transaction Reference",
                    key=f"owner_verify_ref_{key_prefix}_{selected_order_id}",
                )
                notes = owner_cols[2].text_input("Notes", key=f"owner_verify_notes_{key_prefix}_{selected_order_id}")
                if st.button("Confirm Payment", use_container_width=True, key=f"owner_verify_payment_{key_prefix}_{selected_order_id}"):
                    order_service.owner_verify_payment(
                        order_id=selected_order_id,
                        amount_received=amount_received,
                        transaction_reference=transaction_reference,
                        notes=notes,
                        owner_email=current_user_email,
                    )
                    data_service.persist_collection("payments")
                    order_service.persist_order_storage(selected_order_id)
                    data_service.persist_collection("notifications")
                    data_service.persist_collection("gmail_queue")
                    st.success("Payment confirmed and order accepted.")
                    st.rerun()
