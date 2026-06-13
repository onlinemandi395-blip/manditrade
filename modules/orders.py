from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.document_service import DocumentService
from services.payment_service import PaymentService
from services.qr_service import QRService


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
    if role in {"manufacturer", "mahajan"}:
        return {
            t("ui.payment_pending"): lambda rows: [
                row
                for row in rows
                if str(row.get("status", "")).upper() == "PAYMENT_PENDING"
                and str(row.get("requester_email", "") or row.get("buyer_email", "")).strip().lower() == current_user_email
            ],
            t("ui.payment_verified"): lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "PAYMENT_VERIFIED"],
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
        role in {"public_buyer", "manufacturer", "mahajan"}
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
        payment_record = payment_service.ensure_payment_link_fields(payment_record)
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
        st.link_button(t("ui.open_upi_link"), upi_link, use_container_width=True)
    st.code(upi_link)
    st.caption(t("ui.pay_using_qr_note"))
    st.info(t("ui.admin_will_verify_payment"))


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


def render_orders_page(rows: list[dict], role: str, *, data_service=None, order_service=None, notification_service=None, session_service=None, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    document_service = DocumentService()
    current_user_email = str(((session_service.get_user() if session_service else {}) or {}).get("email", "")).strip().lower()
    tab_map = _tabs_for_role(role, current_user_email, translator)
    tabs = st.tabs(list(tab_map.keys()))
    for tab, (label, filter_fn) in zip(tabs, tab_map.items()):
        with tab:
            key_prefix = f"{role}_{label}_{str(label).strip().lower().replace(' ', '_')}"
            filtered_rows = filter_fn(rows)
            render_table(filtered_rows, caption=label)
            if not filtered_rows:
                continue
            order_map = {str(row.get("order_id", "")).strip(): row for row in filtered_rows if str(row.get("order_id", "")).strip()}
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
            invoice_html = document_service.build_invoice_html(selected_order)
            st.download_button(
                t("ui.download_invoice"),
                data=invoice_html.encode("utf-8"),
                file_name=f"{selected_order_id}_invoice.html",
                mime="text/html",
                key=f"download_invoice_{key_prefix}_{selected_order_id}",
            )
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
                if data_service is not None and order_service is not None and session_service is not None:
                    st.markdown(f"##### {t('ui.admin_cleanup')}")
                    if st.button(t("ui.delete_order"), use_container_width=True, type="primary", key=f"delete_order_{key_prefix}_{selected_order_id}"):
                        try:
                            result = order_service.delete_order_for_admin(
                                order_id=selected_order_id,
                                deleted_by=session_service.get_user().get("email", ""),
                            )
                            order_service.persist_order_storage(selected_order_id)
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

                    current_status = str(selected_order.get("status", "")).upper()
                    if current_status == "PAYMENT_PENDING":
                        st.markdown(f"##### {t('ui.admin_action_verify_payment')}")
                        verify_cols = st.columns(3)
                        amount_received = verify_cols[0].number_input(
                            t("ui.amount_received"),
                            min_value=0.0,
                            step=1.0,
                            value=float(selected_order.get("total_amount", 0) or 0),
                            key=f"orders_verify_amount_{key_prefix}_{selected_order_id}",
                        )
                        transaction_reference = verify_cols[1].text_input(
                            t("ui.transaction_reference"),
                            key=f"orders_verify_ref_{key_prefix}_{selected_order_id}",
                        )
                        notes = verify_cols[2].text_input(
                            t("ui.notes"),
                            key=f"orders_verify_notes_{key_prefix}_{selected_order_id}",
                        )
                        if st.button(t("ui.verify_payment"), use_container_width=True, key=f"orders_verify_payment_{key_prefix}_{selected_order_id}"):
                            order_service.verify_payment(
                                order_id=selected_order_id,
                                amount_received=amount_received,
                                transaction_reference=transaction_reference,
                                notes=notes,
                                verified_by=session_service.get_user().get("email", ""),
                            )
                            data_service.persist_collection("payments")
                            order_service.persist_order_storage(selected_order_id)
                            data_service.persist_collection("notifications")
                            data_service.persist_collection("gmail_queue")
                            st.success(t("ui.payment_verified_from_orders_page"))
                            st.rerun()
                    elif current_status == "READY_FOR_PICKUP":
                        st.markdown(f"##### {t('ui.admin_action_assign_delivery_partner')}")
                        users = data_service.get_collection_ref("users")
                        delivery_partners = [
                            row for row in users
                            if str(row.get("role", "")).strip().lower() == "delivery_partner"
                            and str(row.get("status", "ACTIVE")).strip().upper() == "ACTIVE"
                        ]
                        if delivery_partners:
                            partner_map = {row.get("email", ""): row for row in delivery_partners}
                            selected_partner_email = st.selectbox(
                                t("role.delivery_partner"),
                                options=[""] + list(partner_map.keys()),
                                format_func=lambda value: (
                                    f"{partner_map[value].get('display_name', value)} ({value})" if value in partner_map else value
                                ),
                                index=([""] + list(partner_map.keys())).index(str(selected_order.get("preferred_delivery_partner_email", "")).strip().lower()) if str(selected_order.get("preferred_delivery_partner_email", "")).strip().lower() in ([""] + list(partner_map.keys())) else 0,
                                key=f"orders_delivery_partner_{key_prefix}_{selected_order_id}",
                            )
                            if st.button(t("ui.assign_pickup"), use_container_width=True, key=f"orders_assign_pickup_{key_prefix}_{selected_order_id}") and selected_partner_email:
                                order_service.assign_delivery_partner(
                                    order_id=selected_order_id,
                                    delivery_partner_email=selected_partner_email,
                                    assigned_by=session_service.get_user().get("email", ""),
                                )
                                order_service.persist_order_storage(selected_order_id)
                                data_service.persist_collection("shipments")
                                data_service.persist_collection("notifications")
                                data_service.persist_collection("gmail_queue")
                                st.success(t("ui.pickup_assigned_from_orders_page"))
                                st.rerun()
                        else:
                            st.caption(t("ui.no_active_delivery_partners"))
            if role == "public_buyer":
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
                    missing_payment_link_fields = (
                        not str(payment_record.get("upi_link", "")).strip()
                        or not str(payment_record.get("qr_payload", "")).strip()
                    )
                    payment_service = PaymentService(data_service, data_service.cache_service)
                    payment_service.ensure_payment_link_fields(payment_record)
                    if missing_payment_link_fields:
                        data_service.persist_collection("payments")
                    _render_payment_panel(payment_record, payment_service=payment_service, translator=translator)
