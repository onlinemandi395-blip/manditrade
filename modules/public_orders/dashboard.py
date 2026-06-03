from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.platform_shell import render_platform_shell
from components.filter_bar import render_filter_bar
from components.order_detail_view import build_order_detail_payload, render_order_detail_view
from components.responsive_layout import render_section_intro
from components.kpi_cards import render_kpi_cards
from utils.deep_links import build_deep_link_target
from utils.page_ui import render_empty_state, render_metric_button_row, render_status_chip


PUBLIC_ORDER_TIMELINE_STEPS = ["PAYMENT_PENDING", "PAID", "CONFIRMED", "DISPATCHED", "OUT_FOR_DELIVERY", "DELIVERED"]
PUBLIC_ORDER_TIMELINE_LABELS = {
    "PAYMENT_PENDING": "Payment Pending",
    "PAID": "Payment Verified",
    "CONFIRMED": "Packing",
    "DISPATCHED": "Dispatched",
    "OUT_FOR_DELIVERY": "Out For Delivery",
    "DELIVERED": "Delivered",
}


def _default_selected_order(orders: list[dict], session_key: str) -> str | None:
    if not orders:
        return None
    deep_link_id = str(st.session_state.get(session_key, "") or "").strip()
    if deep_link_id and any(item.get("public_order_id") == deep_link_id for item in orders):
        return deep_link_id
    return orders[0]["public_order_id"]


def _render_order_detail(order: dict) -> None:
    detail = build_order_detail_payload(
        order,
        order_id_key="public_order_id",
        status=str(order.get("status", "")),
        items=[
            {
                "name": item.get("product_name", item.get("product_id", "Product")),
                "qty": item.get("qty", 0),
                "unit": item.get("unit", ""),
                "unit_price": item.get("marketplace_price", item.get("price", 0)),
                "subtotal": float(item.get("marketplace_price", item.get("price", 0)) or 0) * float(item.get("qty", 0) or 0),
                "thumbnail_url": item.get("thumbnail_url", ""),
                "image_url": item.get("image_url", ""),
            }
            for item in order.get("items", [])
        ],
        timeline_steps=PUBLIC_ORDER_TIMELINE_STEPS,
        timeline_labels=PUBLIC_ORDER_TIMELINE_LABELS,
        status_history=list(order.get("status_history", [])),
        logistics=dict(order.get("logistics", {})),
        payment={
            "payment_status": order.get("payment_status", ""),
            "payment_receiver": order.get("payment_receiver", ""),
            "payment_reference": order.get("payment_reference", ""),
            "payment_proof_url": order.get("payment_proof_url", ""),
            "payment_verified_by": order.get("payment_verified_by", ""),
            "payment_verified_at": order.get("payment_verified_at", ""),
        },
        trust_badges=[],
        next_action=build_deep_link_target("PUBLIC_ORDER", str(order.get("public_order_id", ""))).get("route", ""),
    )
    render_order_detail_view(detail)


def render_public_orders_dashboard(app_context: dict, *, buyer_mode: bool = False) -> None:
    user = app_context["current_user"]
    service = app_context["public_order_service"]
    trust_badge_service = app_context.get("trust_badge_service")
    page_key = "marketplace_orders_buyer" if buyer_mode else "marketplace_orders_seller"
    title = "My Orders" if buyer_mode else "Public Orders"
    subtitle = (
        "Track your instant-pay public marketplace orders from payment reference through delivery."
        if buyer_mode
        else "Verify payments, confirm, and dispatch public marketplace orders assigned to sellers."
    )
    render_platform_shell(
        title=title,
        subtitle=subtitle,
        badges=["Public Marketplace", "Instant Pay"],
        role=user.role.replace("_", " ").title() if user else "Public",
        breadcrumbs=["Workspace", "Orders", title],
    )
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
        render_kpi_cards(
            [
                {"label": "My Public Orders", "value": str(len(orders)), "status": "SUCCESS"},
                {"label": "Payment Pending", "value": str(len([item for item in orders if item.get("status") == "PAYMENT_PENDING"])), "status": "PENDING"},
                {"label": "Dispatched", "value": str(len([item for item in orders if item.get("status") == "DISPATCHED"])), "status": "OPEN"},
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
            render_empty_state("No Marketplace Orders Yet")
            return
        overview_tab, orders_tab, payments_tab, delivery_tab = st.tabs(["Overview", "Orders", "Payments", "Delivery"])
        default_id = _default_selected_order(orders, "deep_link::marketplace_orders")
        selected_id = st.selectbox("My Order", [item["public_order_id"] for item in orders], index=[item["public_order_id"] for item in orders].index(default_id) if default_id else 0)
        selected = next(item for item in orders if item["public_order_id"] == selected_id)
        with overview_tab:
            _render_order_detail(selected)
        with orders_tab:
            filtered_orders = render_data_grid(
                page_key=f"{page_key}_orders",
                rows=orders,
                search_fields=["public_order_id", "assigned_seller_manufacturer_id", "buyer_email"],
                status_field="status",
                date_field="updated_at",
                price_field="total_amount",
                search_placeholder="Search by order ID or seller",
            )
            if not filtered_orders:
                render_empty_state("No Marketplace Orders Yet")
        with payments_tab:
            if selected.get("status") == "PAYMENT_PENDING":
                st.code(service.build_payment_instruction_text(selected))
                payment_reference = st.text_input("Payment Reference / UTR", key=f"buyer_ref_{selected_id}")
                screenshot_placeholder = st.text_input("Payment Proof URL", key=f"buyer_shot_{selected_id}")
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
            if selected.get("status") == "DELIVERED":
                rating = st.slider("Rate Product", min_value=1, max_value=5, value=5, key=f"buyer_rating_{selected_id}")
                feedback = st.text_area("Feedback", key=f"buyer_feedback_{selected_id}")
                if st.button("Submit Rating", use_container_width=True, key=f"submit_rating_{selected_id}"):
                    service.submit_feedback(selected_id, rating=rating, feedback=feedback, submitted_by=user.email)
                    st.success("Thanks for the feedback.")
                    st.rerun()
        with delivery_tab:
            if selected.get("status") == "DISPATCHED" and st.button("Confirm Delivery", use_container_width=True, key=f"confirm_public_delivery_{selected_id}"):
                try:
                    service.confirm_delivery(selected_id, user)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                else:
                    st.success("Public order marked as delivered.")
                    st.rerun()
            if st.button("Repeat This Order", use_container_width=True, key=f"repeat_public_order_{selected_id}"):
                for item in selected.get("items", []):
                    service.public_cart_service.add_item(
                        buyer["public_buyer_id"],
                        product_id=str(item.get("product_id", "")),
                        qty=int(item.get("qty", 1) or 1),
                    )
                st.success("Cart prefilled from previous order.")
                st.rerun()
            if selected.get("status") != "DISPATCHED":
                render_empty_state("No delivery confirmation action pending for the selected order.")
        return

    if user.role == "platform_admin":
        orders = service.list_all_orders()
    elif user.role in {"manufacturer", "admin_as_manufacturer"}:
        orders = service.list_orders_for_seller(user.manufacturer_code or "")
    else:
        st.info("Public order operations are available to platform admin and seller manufacturers.")
        return
    render_kpi_cards(
        [
            {"label": "Public Orders", "value": str(len(orders)), "status": "SUCCESS"},
            {"label": "Payment Submitted", "value": str(len([item for item in orders if item.get("payment_status") == "SUBMITTED"])), "status": "PENDING"},
            {"label": "Ready To Dispatch", "value": str(len([item for item in orders if item.get("status") == "CONFIRMED"])), "status": "OPEN"},
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
        render_empty_state("No Marketplace Orders Yet")
        return
    overview_tab, orders_tab, payments_tab, delivery_tab = st.tabs(["Overview", "Orders", "Payments", "Delivery"])
    default_id = _default_selected_order(orders, "deep_link::marketplace_orders")
    selected_id = st.selectbox("Public Order", [item["public_order_id"] for item in orders], index=[item["public_order_id"] for item in orders].index(default_id) if default_id else 0)
    selected = next(item for item in orders if item["public_order_id"] == selected_id)
    note = st.text_area("Seller/Admin Note", key=f"public_order_note_{selected_id}")
    with overview_tab:
        _render_order_detail(selected)
    with orders_tab:
        filtered_orders = render_filter_bar(
            page_key=f"{page_key}_seller_orders",
            rows=orders,
            search_fields=["public_order_id", "assigned_seller_manufacturer_id", "buyer_email"],
            status_field="status",
            date_field="updated_at",
            price_field="total_amount",
            search_placeholder="Search by order ID or buyer",
        )
        if filtered_orders:
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_orders), file_name="marketplace-orders-seller.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_orders), file_name="marketplace-orders-seller.json", mime="application/json", use_container_width=True)
            st.dataframe(filtered_orders, use_container_width=True)
        else:
            render_empty_state("No Marketplace Orders Yet")
    with payments_tab:
        proof_url = selected.get("payment_proof_url", "") or selected.get("payment_screenshot_placeholder", "")
        if proof_url:
            st.caption(f"Payment Proof: {proof_url}")
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
            render_empty_state("No payment verification action pending for the selected order.")
    with delivery_tab:
        st.dataframe([selected.get("logistics", {})], use_container_width=True)
        if user.role == "platform_admin":
            with st.form(f"public_logistics_{selected_id}"):
                col1, col2 = st.columns(2)
                transport_mode = col1.text_input("Transport Mode", value=str(selected.get("logistics", {}).get("transport_mode", "")))
                delivery_status = col2.text_input("Delivery Status", value=str(selected.get("logistics", {}).get("delivery_status", "")))
                driver_name = col1.text_input("Driver Name", value=str(selected.get("logistics", {}).get("driver_name", "")))
                driver_mobile = col2.text_input("Driver Mobile", value=str(selected.get("logistics", {}).get("driver_mobile", "")))
                vehicle_number = col1.text_input("Vehicle Number", value=str(selected.get("logistics", {}).get("vehicle_number", "")))
                proof_url = col2.text_input("Proof Image URL", value=str(selected.get("logistics", {}).get("proof_image_url", selected.get('logistics', {}).get("proof_url", ""))))
                expected_delivery = col1.text_input("Expected Delivery", value=str(selected.get("logistics", {}).get("expected_delivery", "")))
                dispatch_note = st.text_area("Dispatch Note", value=str(selected.get("logistics", {}).get("dispatch_note", "")))
                save_logistics = st.form_submit_button("Save Logistics Update")
            if save_logistics:
                service.update_logistics(
                    selected_id,
                    actor=user,
                    transport_mode=transport_mode,
                    driver_name=driver_name,
                    driver_mobile=driver_mobile,
                    vehicle_number=vehicle_number,
                    dispatch_note=dispatch_note,
                    proof_url=proof_url,
                    delivery_status=delivery_status,
                    expected_delivery=expected_delivery,
                )
                st.success("Logistics updated.")
                st.rerun()
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
        if selected.get("status") not in {"PAID", "CONFIRMED"}:
            st.caption("No dispatch transition is pending for the selected order.")
        badges = trust_badge_service.badges_for_marketplace_order(selected) if trust_badge_service else []
        if badges:
            st.caption("Trust Badges: " + " | ".join(badges))
