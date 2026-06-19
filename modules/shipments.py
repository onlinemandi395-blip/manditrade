from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.document_service import DocumentService


def _decorate_shipment_rows(shipments: list[dict], orders: list[dict]) -> list[dict]:
    order_map = {
        str(row.get("order_id", "")).strip(): row
        for row in orders
        if str(row.get("order_id", "")).strip()
    }
    decorated = []
    for shipment in shipments:
        order = dict(order_map.get(str(shipment.get("order_id", "")).strip(), {}) or {})
        financials = dict(order.get("financials", {}) or {})
        service_config = dict(order.get("service_config", {}) or {})
        decorated.append(
            {
                **shipment,
                "source_channel": shipment.get("source_channel", order.get("source_channel", "")),
                "market_type": shipment.get("market_type", order.get("market_type", "")),
                "shipping_mode": shipment.get("shipping_mode", service_config.get("shipping_mode", "owner")),
                "delivery_scope": shipment.get("delivery_scope", service_config.get("delivery_scope", "custom")),
                "shipping_charge": shipment.get("shipping_charge", financials.get("shipping_charge", 0)),
                "packaging_charge": shipment.get("packaging_charge", financials.get("packaging_charge", 0)),
            }
        )
    return decorated


def render_shipments_page(data_service, order_service, notification_service, session_service, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    document_service = DocumentService()
    user = session_service.get_user()
    role = str(user.get("role", "")).strip().lower()
    email = str(user.get("email", "")).strip().lower()
    orders = data_service.get_collection_ref("orders")
    shipments = _decorate_shipment_rows(data_service.get_collection_ref("shipments"), orders)
    users = data_service.get_collection_ref("users")

    if role == "platform_admin":
        tabs = st.tabs([t("ui.ready_for_pickup"), t("ui.assigned_pickups"), t("ui.in_transit"), t("ui.all_shipments")])
        with tabs[0]:
            ready_orders = [row for row in orders if str(row.get("status", "")).upper() == "READY_FOR_PICKUP"]
            render_table(ready_orders, caption=t("ui.ready_for_pickup_orders"))
            st.info("Shipment assignment is managed by the mahajan. Admin can monitor progress here.")
        with tabs[1]:
            assigned_shipments = [row for row in shipments if str(row.get("status", "")).upper() in {"PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT"}]
            render_table(assigned_shipments, caption=t("ui.assigned_pickups"))
        with tabs[2]:
            in_transit_shipments = [row for row in shipments if str(row.get("status", "")).upper() == "IN_TRANSIT"]
            render_table(in_transit_shipments, caption=t("ui.in_transit"))
        with tabs[3]:
            render_table(shipments, caption=t("ui.all_shipments"))
        return

    if role in {"manufacturer", "mahajan"}:
        my_orders = [row for row in orders if str(row.get("owner_email", "")).strip().lower() == email]
        tabs = st.tabs(["Payment Pending", t("ui.accepted"), t("ui.ready_for_pickup"), t("ui.my_shipments")])
        with tabs[0]:
            payment_pending = [row for row in my_orders if str(row.get("status", "")).upper() == "PAYMENT_PENDING"]
            render_table(payment_pending, caption="Orders awaiting your payment confirmation")
        with tabs[1]:
            accepted_orders = [row for row in my_orders if str(row.get("status", "")).upper() == "OWNER_ACCEPTED"]
            render_table(accepted_orders, caption=t("ui.accepted_orders"))
            selected_ready_order_id = st.selectbox(t("ui.accepted_order"), options=[""] + [row.get("order_id", "") for row in accepted_orders], key="owner_ready_pickup_order")
            if st.button(t("ui.mark_ready_for_pickup"), use_container_width=True, key="owner_mark_ready") and selected_ready_order_id:
                order_service.owner_mark_ready_for_pickup(order_id=selected_ready_order_id, owner_email=email)
                order_service.persist_order_storage(selected_ready_order_id)
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success(t("ui.order_marked_ready_for_pickup"))
                st.rerun()
        with tabs[2]:
            ready_orders = [row for row in my_orders if str(row.get("status", "")).upper() in {"READY_FOR_PICKUP", "PICKUP_ASSIGNED", "PICKED_UP"}]
            render_table(ready_orders, caption=t("ui.ready_assigned_picked_up"))
            assignable_orders = [row for row in my_orders if str(row.get("status", "")).upper() == "READY_FOR_PICKUP"]
            delivery_partners = [
                row for row in users
                if str(row.get("role", "")).strip().lower() == "delivery_partner"
                and str(row.get("status", "ACTIVE")).strip().upper() == "ACTIVE"
            ]
            if assignable_orders and delivery_partners:
                order_map = {row.get("order_id", ""): row for row in assignable_orders}
                partner_map = {row.get("email", ""): row for row in delivery_partners}
                selected_order_id = st.selectbox("Ready Order", options=[""] + list(order_map.keys()), key="owner_shipments_ready_order")
                selected_partner_email = st.selectbox(
                    t("role.delivery_partner"),
                    options=[""] + list(partner_map.keys()),
                    format_func=lambda value: (
                        f"{partner_map[value].get('display_name', value)} ({value})" if value in partner_map else value
                    ),
                    index=([""] + list(partner_map.keys())).index(str(order_map.get(selected_order_id, {}).get("preferred_delivery_partner_email", "")).strip().lower()) if str(order_map.get(selected_order_id, {}).get("preferred_delivery_partner_email", "")).strip().lower() in ([""] + list(partner_map.keys())) else 0,
                    key="owner_shipments_delivery_partner",
                )
                if st.button(t("ui.assign_pickup"), use_container_width=True, key="owner_shipments_assign_pickup") and selected_order_id and selected_partner_email:
                    shipment = order_service.assign_delivery_partner(
                        order_id=selected_order_id,
                        delivery_partner_email=selected_partner_email,
                        assigned_by=email,
                    )
                    order_service.persist_order_storage(selected_order_id)
                    data_service.persist_collection("shipments")
                    data_service.persist_collection("notifications")
                    data_service.persist_collection("gmail_queue")
                    st.success(f"{t('ui.pickup_assigned')}: {shipment.get('shipment_id', '')}")
                    st.rerun()
            elif assignable_orders and not delivery_partners:
                st.info(t("ui.no_active_delivery_partners"))
        with tabs[3]:
            my_shipments = [row for row in shipments if str(row.get("owner_email", "")).strip().lower() == email]
            render_table(my_shipments, caption=t("ui.my_shipments"))
        return

    if role == "delivery_partner":
        my_shipments = [row for row in shipments if str(row.get("delivery_partner_email", "")).strip().lower() == email]
        tabs = st.tabs([t("ui.pickup_queue"), t("ui.picked_up"), t("ui.in_transit"), t("ui.delivered"), t("ui.all_assigned")])
        with tabs[0]:
            pickup_queue = [row for row in my_shipments if str(row.get("status", "")).upper() == "PICKUP_ASSIGNED"]
            render_table(pickup_queue, caption=t("ui.pickup_queue"))
            selected_shipment_order_id = st.selectbox(t("ui.assigned_order"), options=[""] + [row.get("order_id", "") for row in pickup_queue], key="delivery_pickup_order")
            if st.button(t("ui.confirm_pickup"), use_container_width=True, key="delivery_confirm_pickup") and selected_shipment_order_id:
                result = order_service.confirm_pickup(order_id=selected_shipment_order_id, delivery_partner_email=email)
                order_service.persist_order_storage(selected_shipment_order_id)
                data_service.persist_collection("shipments")
                data_service.persist_collection("ledger")
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success(f"{t('ui.pickup_confirmed_otp_generated')} {result['order'].get('order_id', '')}.")
                st.rerun()
        with tabs[1]:
            picked_up = [row for row in my_shipments if str(row.get("status", "")).upper() == "PICKED_UP"]
            render_table(picked_up, caption=t("ui.picked_up"))
            selected_in_transit_order_id = st.selectbox(t("ui.picked_up_order"), options=[""] + [row.get("order_id", "") for row in picked_up], key="delivery_in_transit_order")
            if st.button(t("ui.mark_in_transit"), use_container_width=True, key="delivery_mark_in_transit") and selected_in_transit_order_id:
                order_service.mark_in_transit(order_id=selected_in_transit_order_id, delivery_partner_email=email)
                order_service.persist_order_storage(selected_in_transit_order_id)
                data_service.persist_collection("shipments")
                st.success(t("ui.shipment_marked_in_transit"))
                st.rerun()
        with tabs[2]:
            in_transit = [row for row in my_shipments if str(row.get("status", "")).upper() == "IN_TRANSIT"]
            render_table(in_transit, caption=t("ui.in_transit"))
            selected_delivery_order_id = st.selectbox(t("ui.in_transit_order"), options=[""] + [row.get("order_id", "") for row in in_transit], key="delivery_verify_order")
            entered_otp = st.text_input(t("ui.delivery_otp"), key="delivery_otp_input")
            if st.button(t("ui.verify_otp_deliver"), use_container_width=True, key="delivery_verify_otp") and selected_delivery_order_id:
                try:
                    order_service.verify_delivery_otp(
                        order_id=selected_delivery_order_id,
                        delivery_partner_email=email,
                        otp_code=entered_otp,
                    )
                    order_service.persist_order_storage(selected_delivery_order_id)
                    data_service.persist_collection("shipments")
                    data_service.persist_collection("notifications")
                    data_service.persist_collection("gmail_queue")
                    st.success(t("ui.delivery_otp_verified_order_completed"))
                    st.rerun()
                except Exception as exc:
                    order_service.persist_order_storage(selected_delivery_order_id)
                    st.error(str(exc))
        with tabs[3]:
            delivered = [row for row in my_shipments if str(row.get("status", "")).upper() == "DELIVERED"]
            render_table(delivered, caption=t("ui.delivered"))
            delivered_order_map = {row.get("order_id", ""): row for row in delivered}
            selected_delivered_order_id = st.selectbox(t("ui.delivered_order"), options=[""] + list(delivered_order_map.keys()), key="delivery_completed_order")
            selected_delivered_shipment = delivered_order_map.get(selected_delivered_order_id, {})
            if selected_delivered_shipment:
                related_order = next((row for row in orders if str(row.get("order_id", "")).strip() == selected_delivered_order_id), {})
                if related_order:
                    slip_html = document_service.build_delivery_slip_html(related_order, selected_delivered_shipment)
                    st.download_button(
                        t("ui.download_delivery_slip"),
                        data=slip_html.encode("utf-8"),
                        file_name=f"{selected_delivered_order_id}_delivery_slip.html",
                        mime="text/html",
                        use_container_width=True,
                        key="delivery_completed_slip_download",
                    )
        with tabs[4]:
            render_table(my_shipments, caption=t("ui.all_assigned_shipments"))
        return

    render_table(shipments, caption=t("module.shipments.title"))
