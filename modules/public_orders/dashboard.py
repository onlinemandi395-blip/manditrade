from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_metric_button_row


def render_public_orders_dashboard(app_context: dict, *, buyer_mode: bool = False) -> None:
    user = app_context["current_user"]
    service = app_context["public_order_service"]
    page_key = "marketplace_orders_buyer" if buyer_mode else "marketplace_orders_seller"
    title = "My Orders" if buyer_mode else "Public Orders"
    subtitle = (
        "Track your instant-pay public marketplace orders from payment reference through delivery."
        if buyer_mode
        else "Verify payments, confirm, and dispatch public marketplace orders assigned to sellers."
    )
    render_page_header(title, subtitle, ["Public Marketplace", "Instant Pay"], role=user.role.replace("_", " ").title() if user else "Public")
    if not user:
        st.info("Sign in as a public buyer or seller role to access public orders.")
        return

    if buyer_mode:
        if user.role != "public_buyer":
            st.info("This page is reserved for signed-in public buyers.")
            return
        buyer = app_context["public_buyer_service"].get_by_email(user.email)
        if not buyer:
            st.info("No public buyer profile is linked to this account yet.")
            return
        orders = service.list_orders_for_buyer(buyer["public_buyer_id"])
        render_metric_grid(
            [
                render_metric_card("My Public Orders", str(len(orders)), "SUCCESS"),
                render_metric_card("Payment Pending", str(len([item for item in orders if item.get("status") == "PAYMENT_PENDING"])), "PENDING"),
                render_metric_card("Dispatched", str(len([item for item in orders if item.get("status") == "DISPATCHED"])), "OPEN"),
            ]
        )
        render_metric_button_row(
            page_key,
            [
                {"label": "Overview", "value": str(len(orders)), "tab_name": "Overview"},
                {"label": "Orders", "value": str(len(orders)), "tab_name": "Orders"},
                {"label": "Payments", "value": str(len([item for item in orders if item.get('status') == 'PAYMENT_PENDING'])), "tab_name": "Payments"},
                {"label": "Delivery", "value": str(len([item for item in orders if item.get('status') == 'DISPATCHED'])), "tab_name": "Delivery"},
            ],
        )
        render_section_intro("Public Order Flow", "Public orders do not create ledger entries. Full payment comes first, then seller verification, confirmation, and dispatch.")
        if not orders:
            st.info("No public marketplace orders found yet.")
            return
        overview_tab, orders_tab, payments_tab, delivery_tab = st.tabs(["Overview", "Orders", "Payments", "Delivery"])
        selected_id = st.selectbox("My Order", [item["public_order_id"] for item in orders])
        selected = next(item for item in orders if item["public_order_id"] == selected_id)
        with overview_tab:
            st.json(selected, expanded=False)
        with orders_tab:
            st.dataframe(orders, use_container_width=True)
        with payments_tab:
            if selected.get("status") == "PAYMENT_PENDING":
                st.code(service.build_payment_instruction_text(selected))
                payment_reference = st.text_input("Payment Reference / UTR", key=f"buyer_ref_{selected_id}")
                screenshot_placeholder = st.text_input("Optional Screenshot Placeholder", key=f"buyer_shot_{selected_id}")
                if st.button("Submit Payment Reference", use_container_width=True, key=f"submit_public_payment_{selected_id}"):
                    try:
                        service.submit_payment_reference(selected_id, buyer["public_buyer_id"], payment_reference=payment_reference, screenshot_placeholder=screenshot_placeholder)
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
                    else:
                        st.success("Payment reference submitted.")
                        st.rerun()
            else:
                st.info("No payment action pending for the selected order.")
        with delivery_tab:
            if selected.get("status") == "DISPATCHED" and st.button("Confirm Delivery", use_container_width=True, key=f"confirm_public_delivery_{selected_id}"):
                try:
                    service.confirm_delivery(selected_id, user)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success("Public order marked as delivered.")
                    st.rerun()
            else:
                st.info("No delivery confirmation action pending for the selected order.")
        return

    if user.role == "platform_admin":
        orders = service.list_all_orders()
    elif user.role in {"manufacturer", "admin_as_manufacturer"}:
        orders = service.list_orders_for_seller(user.manufacturer_code or "")
    else:
        st.info("Public order operations are available to platform admin and seller manufacturers.")
        return
    render_metric_grid(
        [
            render_metric_card("Public Orders", str(len(orders)), "SUCCESS"),
            render_metric_card("Payment Submitted", str(len([item for item in orders if item.get("payment_status") == "SUBMITTED"])), "PENDING"),
            render_metric_card("Ready To Dispatch", str(len([item for item in orders if item.get("status") == "CONFIRMED"])), "OPEN"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(len(orders)), "tab_name": "Overview"},
            {"label": "Orders", "value": str(len(orders)), "tab_name": "Orders"},
            {"label": "Payments", "value": str(len([item for item in orders if item.get('payment_status') == 'SUBMITTED'])), "tab_name": "Payments"},
            {"label": "Delivery", "value": str(len([item for item in orders if item.get('status') == 'CONFIRMED'])), "tab_name": "Delivery"},
        ],
    )
    render_section_intro("Seller Fulfilment", "Public orders consume seller self inventory after payment verification. They do not use mandi inventory automatically.")
    if not orders:
        st.info("No public orders are assigned to this view.")
        return
    overview_tab, orders_tab, payments_tab, delivery_tab = st.tabs(["Overview", "Orders", "Payments", "Delivery"])
    selected_id = st.selectbox("Public Order", [item["public_order_id"] for item in orders])
    selected = next(item for item in orders if item["public_order_id"] == selected_id)
    note = st.text_area("Seller/Admin Note", key=f"public_order_note_{selected_id}")
    with overview_tab:
        st.json(selected, expanded=False)
    with orders_tab:
        st.dataframe(orders, use_container_width=True)
    with payments_tab:
        if selected.get("payment_status") == "SUBMITTED":
            col1, col2 = st.columns(2)
            if col1.button("Verify Payment", use_container_width=True, key=f"verify_public_payment_{selected_id}"):
                try:
                    service.verify_payment(selected_id, user, approved=True, note=note)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success("Public payment verified.")
                    st.rerun()
            if col2.button("Reject Payment", use_container_width=True, key=f"reject_public_payment_{selected_id}"):
                try:
                    service.verify_payment(selected_id, user, approved=False, note=note)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.warning("Payment rejected and order returned to payment pending.")
                    st.rerun()
        else:
            st.info("No payment verification action pending for the selected order.")
    with delivery_tab:
        if selected.get("status") == "PAID" and st.button("Confirm Public Order", use_container_width=True, key=f"confirm_public_order_{selected_id}"):
            try:
                service.confirm_order(selected_id, user)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.success("Public order confirmed.")
                st.rerun()
        if selected.get("status") == "CONFIRMED" and st.button("Dispatch Public Order", use_container_width=True, key=f"dispatch_public_order_{selected_id}"):
            try:
                service.dispatch_order(selected_id, user)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
            else:
                st.success("Public order dispatched.")
                st.rerun()
