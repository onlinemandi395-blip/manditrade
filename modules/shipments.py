from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.document_service import DocumentService


def render_shipments_page(data_service, order_service, notification_service, session_service) -> None:
    document_service = DocumentService()
    user = session_service.get_user()
    role = str(user.get("role", "")).strip().lower()
    email = str(user.get("email", "")).strip().lower()
    orders = data_service.get_collection_ref("orders")
    shipments = data_service.get_collection_ref("shipments")
    users = data_service.get_collection_ref("users")

    if role == "platform_admin":
        tabs = st.tabs(["Ready For Pickup", "Assigned Pickups", "In Transit", "All Shipments"])
        with tabs[0]:
            ready_orders = [row for row in orders if str(row.get("status", "")).upper() == "READY_FOR_PICKUP"]
            render_table(ready_orders, caption="Ready For Pickup Orders")
            delivery_partners = [
                row for row in users
                if str(row.get("role", "")).strip().lower() == "delivery_partner"
                and str(row.get("status", "ACTIVE")).strip().upper() == "ACTIVE"
            ]
            if ready_orders and delivery_partners:
                order_map = {row.get("order_id", ""): row for row in ready_orders}
                partner_map = {row.get("email", ""): row for row in delivery_partners}
                selected_order_id = st.selectbox("Ready Order", options=[""] + list(order_map.keys()), key="shipments_ready_order")
                selected_partner_email = st.selectbox(
                    "Delivery Partner",
                    options=[""] + list(partner_map.keys()),
                    format_func=lambda value: (
                        f"{partner_map[value].get('display_name', value)} ({value})" if value in partner_map else value
                    ),
                    index=([""] + list(partner_map.keys())).index(str(order_map.get(selected_order_id, {}).get("preferred_delivery_partner_email", "")).strip().lower()) if str(order_map.get(selected_order_id, {}).get("preferred_delivery_partner_email", "")).strip().lower() in ([""] + list(partner_map.keys())) else 0,
                    key="shipments_delivery_partner",
                )
                if st.button("Assign Pickup", use_container_width=True, key="shipments_assign_pickup") and selected_order_id and selected_partner_email:
                    shipment = order_service.assign_delivery_partner(
                        order_id=selected_order_id,
                        delivery_partner_email=selected_partner_email,
                        assigned_by=email,
                    )
                    order_service.persist_order_storage(selected_order_id)
                    data_service.persist_collection("shipments")
                    data_service.persist_collection("notifications")
                    data_service.persist_collection("gmail_queue")
                    st.success(f"Pickup assigned: {shipment.get('shipment_id', '')}")
                    st.rerun()
            elif ready_orders and not delivery_partners:
                st.info("No active delivery partners found.")
        with tabs[1]:
            assigned_shipments = [row for row in shipments if str(row.get("status", "")).upper() in {"PICKUP_ASSIGNED", "PICKED_UP", "IN_TRANSIT"}]
            render_table(assigned_shipments, caption="Assigned Pickups")
        with tabs[2]:
            in_transit_shipments = [row for row in shipments if str(row.get("status", "")).upper() == "IN_TRANSIT"]
            render_table(in_transit_shipments, caption="In Transit")
        with tabs[3]:
            render_table(shipments, caption="All Shipments")
        return

    if role in {"manufacturer", "mahajan"}:
        my_orders = [row for row in orders if str(row.get("owner_email", "")).strip().lower() == email]
        tabs = st.tabs(["Payment Verified", "Accepted", "Ready For Pickup", "My Shipments"])
        with tabs[0]:
            payment_verified = [row for row in my_orders if str(row.get("status", "")).upper() == "PAYMENT_VERIFIED"]
            render_table(payment_verified, caption="Payment Verified Orders")
            selected_order_id = st.selectbox("Order", options=[""] + [row.get("order_id", "") for row in payment_verified], key="owner_payment_verified_order")
            action = st.selectbox("Action", options=["ACCEPT", "REJECT"], key="owner_order_action")
            reject_reason = st.text_area("Reject Reason", key="owner_reject_reason")
            if st.button("Apply Owner Action", use_container_width=True, key="owner_apply_action") and selected_order_id:
                if action == "ACCEPT":
                    order_service.owner_accept_order(order_id=selected_order_id, owner_email=email)
                else:
                    order_service.owner_reject_order(order_id=selected_order_id, owner_email=email, reason=reject_reason)
                order_service.persist_order_storage(selected_order_id)
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success("Owner action applied.")
                st.rerun()
        with tabs[1]:
            accepted_orders = [row for row in my_orders if str(row.get("status", "")).upper() == "OWNER_ACCEPTED"]
            render_table(accepted_orders, caption="Accepted Orders")
            selected_ready_order_id = st.selectbox("Accepted Order", options=[""] + [row.get("order_id", "") for row in accepted_orders], key="owner_ready_pickup_order")
            if st.button("Mark Ready For Pickup", use_container_width=True, key="owner_mark_ready") and selected_ready_order_id:
                order_service.owner_mark_ready_for_pickup(order_id=selected_ready_order_id, owner_email=email)
                order_service.persist_order_storage(selected_ready_order_id)
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success("Order marked ready for pickup.")
                st.rerun()
        with tabs[2]:
            ready_orders = [row for row in my_orders if str(row.get("status", "")).upper() in {"READY_FOR_PICKUP", "PICKUP_ASSIGNED", "PICKED_UP"}]
            render_table(ready_orders, caption="Ready / Assigned / Picked Up")
        with tabs[3]:
            my_shipments = [row for row in shipments if str(row.get("owner_email", "")).strip().lower() == email]
            render_table(my_shipments, caption="My Shipments")
        return

    if role == "delivery_partner":
        my_shipments = [row for row in shipments if str(row.get("delivery_partner_email", "")).strip().lower() == email]
        tabs = st.tabs(["Pickup Queue", "Picked Up", "In Transit", "Delivered", "All Assigned"])
        with tabs[0]:
            pickup_queue = [row for row in my_shipments if str(row.get("status", "")).upper() == "PICKUP_ASSIGNED"]
            render_table(pickup_queue, caption="Pickup Queue")
            selected_shipment_order_id = st.selectbox("Assigned Order", options=[""] + [row.get("order_id", "") for row in pickup_queue], key="delivery_pickup_order")
            if st.button("Confirm Pickup", use_container_width=True, key="delivery_confirm_pickup") and selected_shipment_order_id:
                result = order_service.confirm_pickup(order_id=selected_shipment_order_id, delivery_partner_email=email)
                order_service.persist_order_storage(selected_shipment_order_id)
                data_service.persist_collection("shipments")
                data_service.persist_collection("ledger")
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success(f"Pickup confirmed. OTP generated for order {result['order'].get('order_id', '')}.")
                st.rerun()
        with tabs[1]:
            picked_up = [row for row in my_shipments if str(row.get("status", "")).upper() == "PICKED_UP"]
            render_table(picked_up, caption="Picked Up")
            selected_in_transit_order_id = st.selectbox("Picked Up Order", options=[""] + [row.get("order_id", "") for row in picked_up], key="delivery_in_transit_order")
            if st.button("Mark In Transit", use_container_width=True, key="delivery_mark_in_transit") and selected_in_transit_order_id:
                order_service.mark_in_transit(order_id=selected_in_transit_order_id, delivery_partner_email=email)
                order_service.persist_order_storage(selected_in_transit_order_id)
                data_service.persist_collection("shipments")
                st.success("Shipment marked in transit.")
                st.rerun()
        with tabs[2]:
            in_transit = [row for row in my_shipments if str(row.get("status", "")).upper() == "IN_TRANSIT"]
            render_table(in_transit, caption="In Transit")
            selected_delivery_order_id = st.selectbox("In Transit Order", options=[""] + [row.get("order_id", "") for row in in_transit], key="delivery_verify_order")
            entered_otp = st.text_input("Delivery OTP", key="delivery_otp_input")
            if st.button("Verify OTP & Deliver", use_container_width=True, key="delivery_verify_otp") and selected_delivery_order_id:
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
                    st.success("Delivery OTP verified. Order completed.")
                    st.rerun()
                except Exception as exc:
                    order_service.persist_order_storage(selected_delivery_order_id)
                    st.error(str(exc))
        with tabs[3]:
            delivered = [row for row in my_shipments if str(row.get("status", "")).upper() == "DELIVERED"]
            render_table(delivered, caption="Delivered")
            delivered_order_map = {row.get("order_id", ""): row for row in delivered}
            selected_delivered_order_id = st.selectbox("Delivered Order", options=[""] + list(delivered_order_map.keys()), key="delivery_completed_order")
            selected_delivered_shipment = delivered_order_map.get(selected_delivered_order_id, {})
            if selected_delivered_shipment:
                related_order = next((row for row in orders if str(row.get("order_id", "")).strip() == selected_delivered_order_id), {})
                if related_order:
                    slip_html = document_service.build_delivery_slip_html(related_order, selected_delivered_shipment)
                    st.download_button(
                        "Download Delivery Slip",
                        data=slip_html.encode("utf-8"),
                        file_name=f"{selected_delivered_order_id}_delivery_slip.html",
                        mime="text/html",
                        use_container_width=True,
                        key="delivery_completed_slip_download",
                    )
        with tabs[4]:
            render_table(my_shipments, caption="All Assigned Shipments")
        return

    render_table(shipments, caption="Shipments")
