from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from services.document_service import DocumentService


def _tabs_for_role(role: str) -> dict[str, callable]:
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
            "All Orders": lambda rows: rows,
            "Marketplace": lambda rows: [row for row in rows if row.get("source_channel") == "marketplace"],
            "MandiTrade": lambda rows: [row for row in rows if row.get("source_channel") == "manditrade"],
            "Payment Pending": lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "PAYMENT_PENDING"],
            "Payment Verified": lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "PAYMENT_VERIFIED"],
            "In Progress": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in active_statuses],
            "Completed": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in completed_statuses],
        }
    if role in {"manufacturer", "mahajan"}:
        return {
            "Payment Verified": lambda rows: [row for row in rows if str(row.get("status", "")).upper() == "PAYMENT_VERIFIED"],
            "Accepted": lambda rows: [row for row in rows if str(row.get("owner_status", "")).upper() == "ACCEPTED"],
            "Ready / Assigned": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in {"READY_FOR_PICKUP", "PICKUP_ASSIGNED", "PICKED_UP"}],
            "In Progress": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in {"IN_TRANSIT"}],
            "Completed": lambda rows: [row for row in rows if str(row.get("status", "")).upper() in completed_statuses],
        }
    return {
        "My Orders": lambda rows: rows,
    }


def _render_buyer_status_tracker(selected_order: dict) -> None:
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
                st.success(stage.replace("_", " ").title())
            elif index == current_index:
                st.info(stage.replace("_", " ").title())
            else:
                st.caption(stage.replace("_", " ").title())


def render_orders_page(rows: list[dict], role: str, *, data_service=None, order_service=None, notification_service=None, session_service=None) -> None:
    document_service = DocumentService()
    tab_map = _tabs_for_role(role)
    tabs = st.tabs(list(tab_map.keys()))
    for tab, (label, filter_fn) in zip(tabs, tab_map.items()):
        with tab:
            filtered_rows = filter_fn(rows)
            render_table(filtered_rows, caption=label)
            if not filtered_rows:
                continue
            order_map = {str(row.get("order_id", "")).strip(): row for row in filtered_rows if str(row.get("order_id", "")).strip()}
            selected_order_id = st.selectbox(
                f"{label} Order Detail",
                options=[""] + list(order_map.keys()),
                key=f"order_detail_{role}_{label}",
            )
            selected_order = order_map.get(selected_order_id)
            if not selected_order:
                continue
            st.markdown("#### Order Detail")
            meta_cols = st.columns(4)
            meta_cols[0].metric("Status", selected_order.get("status", ""))
            meta_cols[1].metric("Payment", selected_order.get("payment_reference", ""))
            meta_cols[2].metric("Owner Status", selected_order.get("owner_status", ""))
            meta_cols[3].metric("Delivery Status", selected_order.get("delivery_status", ""))
            st.caption(
                f"Product: {selected_order.get('product_name', '')} | "
                f"Qty: {selected_order.get('quantity', 0)} | "
                f"Amount: {selected_order.get('total_amount', 0)}"
            )
            invoice_html = document_service.build_invoice_html(selected_order)
            st.download_button(
                "Download Invoice",
                data=invoice_html.encode("utf-8"),
                file_name=f"{selected_order_id}_invoice.html",
                mime="text/html",
                key=f"download_invoice_{role}_{selected_order_id}",
            )
            if data_service is not None:
                shipment_rows = data_service.get_collection_ref("shipments")
                related_shipment = next((row for row in shipment_rows if str(row.get("order_id", "")).strip() == selected_order_id), {})
                if related_shipment:
                    delivery_slip_html = document_service.build_delivery_slip_html(selected_order, related_shipment)
                    st.download_button(
                        "Download Delivery Slip",
                        data=delivery_slip_html.encode("utf-8"),
                        file_name=f"{selected_order_id}_delivery_slip.html",
                        mime="text/html",
                        key=f"download_delivery_slip_{role}_{selected_order_id}",
                    )
            if role == "platform_admin":
                st.info(
                    f"Next action: admin_status={selected_order.get('admin_status', '')}, "
                    f"payment_id={selected_order.get('payment_id', '')}"
                )
                if data_service is not None and order_service is not None and session_service is not None:
                    current_status = str(selected_order.get("status", "")).upper()
                    if current_status == "PAYMENT_PENDING":
                        st.markdown("##### Admin Action: Verify Payment")
                        verify_cols = st.columns(3)
                        amount_received = verify_cols[0].number_input(
                            "Amount Received",
                            min_value=0.0,
                            step=1.0,
                            value=float(selected_order.get("total_amount", 0) or 0),
                            key=f"orders_verify_amount_{selected_order_id}",
                        )
                        transaction_reference = verify_cols[1].text_input(
                            "Transaction Reference",
                            key=f"orders_verify_ref_{selected_order_id}",
                        )
                        notes = verify_cols[2].text_input(
                            "Notes",
                            key=f"orders_verify_notes_{selected_order_id}",
                        )
                        if st.button("Verify Payment", use_container_width=True, key=f"orders_verify_payment_{selected_order_id}"):
                            order_service.verify_payment(
                                order_id=selected_order_id,
                                amount_received=amount_received,
                                transaction_reference=transaction_reference,
                                notes=notes,
                                verified_by=session_service.get_user().get("email", ""),
                            )
                            data_service.persist_collection("payments")
                            data_service.persist_collection("orders")
                            data_service.persist_collection("notifications")
                            data_service.persist_collection("gmail_queue")
                            st.success("Payment verified from Orders page.")
                            st.rerun()
                    elif current_status == "READY_FOR_PICKUP":
                        st.markdown("##### Admin Action: Assign Delivery Partner")
                        users = data_service.get_collection_ref("users")
                        delivery_partners = [
                            row for row in users
                            if str(row.get("role", "")).strip().lower() == "delivery_partner"
                            and str(row.get("status", "ACTIVE")).strip().upper() == "ACTIVE"
                        ]
                        if delivery_partners:
                            partner_map = {row.get("email", ""): row for row in delivery_partners}
                            selected_partner_email = st.selectbox(
                                "Delivery Partner",
                                options=[""] + list(partner_map.keys()),
                                format_func=lambda value: (
                                    f"{partner_map[value].get('display_name', value)} ({value})" if value in partner_map else value
                                ),
                                index=([""] + list(partner_map.keys())).index(str(selected_order.get("preferred_delivery_partner_email", "")).strip().lower()) if str(selected_order.get("preferred_delivery_partner_email", "")).strip().lower() in ([""] + list(partner_map.keys())) else 0,
                                key=f"orders_delivery_partner_{selected_order_id}",
                            )
                            if st.button("Assign Pickup", use_container_width=True, key=f"orders_assign_pickup_{selected_order_id}") and selected_partner_email:
                                order_service.assign_delivery_partner(
                                    order_id=selected_order_id,
                                    delivery_partner_email=selected_partner_email,
                                    assigned_by=session_service.get_user().get("email", ""),
                                )
                                data_service.persist_collection("orders")
                                data_service.persist_collection("shipments")
                                data_service.persist_collection("notifications")
                                data_service.persist_collection("gmail_queue")
                                st.success("Pickup assigned from Orders page.")
                                st.rerun()
                        else:
                            st.caption("No active delivery partners found.")
            if role == "public_buyer":
                st.markdown("#### Order Status Tracker")
                _render_buyer_status_tracker(selected_order)
                otp_status = str(selected_order.get("otp_status", "")).upper()
                if otp_status in {"GENERATED", "VERIFIED"} and str(selected_order.get("delivery_otp", "")).strip():
                    st.success(f"Delivery OTP: {selected_order.get('delivery_otp', '')}")
                else:
                    st.caption("Delivery OTP will appear here after pickup.")
