from __future__ import annotations

from typing import Any

import streamlit as st

from components.filter_bar import render_filter_bar
from components.order_detail_view import build_order_detail_payload, render_order_detail_view
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.deep_links import build_deep_link_target
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import get_active_filter, render_empty_state, render_metric_button_row, render_status_chip

MANDI_TIMELINE_STEPS = [
    "REQUESTED_BY_MANUFACTURER",
    "ADMIN_REVIEWING",
    "SENT_TO_MAHAJAN",
    "MAHAJAN_QUOTED",
    "ADMIN_PRICE_SET",
    "MANUFACTURER_CONFIRMED",
    "MAHAJAN_DISPATCHED",
    "MANUFACTURER_RECEIVED",
    "CLOSED",
]

MANDI_TIMELINE_LABELS = {
    "REQUESTED_BY_MANUFACTURER": "Manufacturer Requested",
    "ADMIN_REVIEWING": "Admin Reviewing",
    "SENT_TO_MAHAJAN": "Sent To Mahajan",
    "MAHAJAN_QUOTED": "Mahajan Quoted",
    "ADMIN_PRICE_SET": "Admin Price Set",
    "MANUFACTURER_CONFIRMED": "Manufacturer Confirmed",
    "MAHAJAN_DISPATCHED": "Mahajan Dispatched",
    "MANUFACTURER_RECEIVED": "Manufacturer Received",
    "CLOSED": "Closed",
    "CANCELLED": "Cancelled",
}

MANDI_ORDER_FILTERS = {
    "OPEN_REQUESTS": {"label": "Open Requests", "statuses": {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING", "SENT_TO_MAHAJAN"}},
    "AWAITING_MAHAJAN_QUOTE": {"label": "Awaiting Mahajan Quote", "statuses": {"SENT_TO_MAHAJAN"}},
    "AWAITING_MANUFACTURER_CONFIRMATION": {"label": "Awaiting Manufacturer Confirmation", "statuses": {"ADMIN_PRICE_SET"}},
    "DISPATCHED": {"label": "Dispatched", "statuses": {"MAHAJAN_DISPATCHED"}},
    "RECEIVED": {"label": "Received", "statuses": {"MANUFACTURER_RECEIVED"}},
    "CLOSED": {"label": "Closed", "statuses": {"CLOSED"}},
}


def get_mandi_timeline_steps() -> list[str]:
    return list(MANDI_TIMELINE_STEPS)


def get_mandi_timeline_labels() -> dict[str, str]:
    return dict(MANDI_TIMELINE_LABELS)


def filter_supply_orders(orders: list[dict[str, Any]], filter_key: str) -> list[dict[str, Any]]:
    statuses = MANDI_ORDER_FILTERS.get(filter_key, {}).get("statuses")
    if not statuses:
        return list(orders)
    return [item for item in orders if item.get("status") in statuses]


def get_supply_order_role_actions(role: str, order: dict[str, Any] | None) -> list[str]:
    if not order:
        return []
    status = str(order.get("status") or "")
    if role == "platform_admin":
        if status in {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING"}:
            return ["Assign Mahajan"]
        if status == "MAHAJAN_QUOTED":
            return ["Set Manufacturer Price"]
        if status == "MANUFACTURER_RECEIVED":
            return ["Close Order"]
        if status not in {"CANCELLED", "CLOSED"}:
            return ["Cancel Order"]
        return []
    if role == "mahajan":
        if status == "SENT_TO_MAHAJAN":
            return ["Submit Quote"]
        if status == "MANUFACTURER_CONFIRMED":
            return ["Dispatch Order"]
        return []
    if role in {"manufacturer", "admin_as_manufacturer"}:
        if status == "ADMIN_PRICE_SET":
            return ["Confirm Admin Price"]
        if status == "MAHAJAN_DISPATCHED":
            return ["Mark Received"]
        return []
    return []


def get_supply_order_next_action(role: str, order: dict[str, Any] | None) -> str:
    actions = get_supply_order_role_actions(role, order)
    if actions:
        return actions[0]
    if order and order.get("status") in {"CLOSED", "CANCELLED"}:
        return "No pending action"
    return "Waiting on another role"


def build_supply_order_detail(
    order: dict[str, Any],
    *,
    role: str,
    raw_materials: dict[str, dict[str, Any]],
    mahajans: dict[str, dict[str, Any]],
    supply_ledger_entries: list[dict[str, Any]],
    mandi_ledger_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    material = raw_materials.get(str(order.get("raw_material_id") or ""), {})
    mahajan = mahajans.get(str(order.get("mahajan_id") or ""), {})
    commission = dict(order.get("commission_object") or {})
    supply_entry = next((item for item in supply_ledger_entries if item.get("mandi_order_id") == order.get("mandi_order_id")), {})
    mandi_entry = next((item for item in mandi_ledger_entries if item.get("metadata", {}).get("supply_order") == order.get("mandi_order_id")), {})
    return {
        "order_id": order.get("mandi_order_id", ""),
        "manufacturer": order.get("manufacturer_id", ""),
        "mahajan": mahajan.get("business_name", order.get("mahajan_id", "")) or "Unassigned",
        "raw_material_items": f"{material.get('name', order.get('raw_material_id', 'Raw Material'))} | Qty {order.get('qty', 0)} {order.get('unit', '')}".strip(),
        "mahajan_price": float(order.get("mahajan_unit_price", 0) or 0),
        "manufacturer_price": float(order.get("manufacturer_unit_price", 0) or 0),
        "admin_earning": float(commission.get("admin_total_earning", 0) or 0),
        "ledger_status": {
            "supply_ledger": supply_entry.get("status", "NOT_CREATED"),
            "mandi_ledger": mandi_entry.get("status", "NOT_CREATED"),
        },
        "current_status": order.get("status", ""),
        "timeline": [MANDI_TIMELINE_LABELS[step] for step in MANDI_TIMELINE_STEPS],
        "next_action": get_supply_order_next_action(role, order),
    }


def _index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(item.get(key) or ""): item for item in items if item.get(key)}


def _get_mandi_ledger_entries(service, manufacturer_code: str) -> list[dict[str, Any]]:
    ledgers = service.ledger_service.list_ledgers(manufacturer_code) if manufacturer_code else []
    entries: list[dict[str, Any]] = []
    for ledger in ledgers:
        for entry in ledger.get("entries", []):
            if entry.get("metadata", {}).get("ledger_scope") == "mandi_ledger":
                entries.append(entry)
    return entries


def _render_supply_order_detail(
    order: dict[str, Any],
    *,
    role: str,
    materials_by_id: dict[str, dict[str, Any]],
    mahajans_by_id: dict[str, dict[str, Any]],
    supply_ledger_entries: list[dict[str, Any]],
    mandi_ledger_entries: list[dict[str, Any]],
) -> None:
    detail = build_supply_order_detail(
        order,
        role=role,
        raw_materials=materials_by_id,
        mahajans=mahajans_by_id,
        supply_ledger_entries=supply_ledger_entries,
        mandi_ledger_entries=mandi_ledger_entries,
    )
    material = materials_by_id.get(str(order.get("raw_material_id") or ""), {})
    render_section_intro("Mandi Order Detail", "Raw Materials belong to the admin/mahajan supply layer. Products remain the manufacturer selling layer.")
    render_status_chip("Current Status", MANDI_TIMELINE_LABELS.get(detail["current_status"], detail["current_status"]))
    render_status_chip("Next Action", detail["next_action"])
    render_order_detail_view(
        build_order_detail_payload(
            order,
            order_id_key="mandi_order_id",
            status=str(order.get("status", "")),
            items=[
                {
                    "name": material.get("name", order.get("raw_material_id", "Raw Material")),
                    "qty": order.get("qty", 0),
                    "unit": order.get("unit", ""),
                    "unit_price": order.get("manufacturer_unit_price", order.get("mahajan_unit_price", 0)),
                    "subtotal": float(order.get("manufacturer_unit_price", order.get("mahajan_unit_price", 0)) or 0) * float(order.get("qty", 0) or 0),
                    "thumbnail_url": material.get("thumbnail_url", ""),
                    "image_url": material.get("image_url", ""),
                }
            ],
            timeline_steps=MANDI_TIMELINE_STEPS,
            timeline_labels=MANDI_TIMELINE_LABELS,
            status_history=list(order.get("internal_status_history", [])),
            logistics=dict(order.get("logistics", {})),
            payment={
                "payment_receiver": order.get("payment_receiver", ""),
                "payment_proof_url": order.get("payment_proof_url", ""),
                "payment_verified_by": order.get("payment_verified_by", ""),
                "payment_verified_at": order.get("payment_verified_at", ""),
                "ledger_status": detail["ledger_status"],
                "mahajan_price": detail["mahajan_price"],
                "manufacturer_price": detail["manufacturer_price"],
                "admin_earning": detail["admin_earning"],
            },
            next_action=detail["next_action"],
            trust_badges=[],
        )
    )


def _render_mandi_order_filters(page_key: str, orders: list[dict[str, Any]]) -> None:
    render_metric_button_row(
        page_key,
        [
            {
                "label": config["label"],
                "value": str(len(filter_supply_orders(orders, filter_key))),
                "tab_name": "Orders",
                "filter_value": filter_key,
                "button_key": f"{page_key}_{filter_key.lower()}",
            }
            for filter_key, config in MANDI_ORDER_FILTERS.items()
        ],
    )


def _render_orders_table(page_key: str, orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_filter = get_active_filter(page_key)
    filtered_orders = filter_supply_orders(orders, active_filter)
    filter_label = MANDI_ORDER_FILTERS.get(active_filter, {}).get("label", "All Orders")
    st.caption(f"Orders filter: {filter_label}")
    visible_orders = filtered_orders if active_filter else orders
    visible_orders = render_filter_bar(
        page_key=f"{page_key}_table",
        rows=visible_orders,
        search_fields=["mandi_order_id", "manufacturer_id", "mahajan_id", "raw_material_id", "notes"],
        status_field="status",
        date_field="updated_at",
        price_field="manufacturer_unit_price",
        search_placeholder="Search by order ID, manufacturer, mahajan, or raw material",
    )
    if visible_orders:
        col1, col2 = st.columns(2)
        col1.download_button("Export Orders CSV", export_rows_to_csv_bytes(visible_orders), file_name="mandi-orders.csv", mime="text/csv", use_container_width=True)
        col2.download_button("Export Orders JSON", export_rows_to_json_bytes(visible_orders), file_name="mandi-orders.json", mime="application/json", use_container_width=True)
        st.dataframe(visible_orders, use_container_width=True)
    else:
        render_empty_state("No mandi orders match the selected filters.")
    if active_filter and not filtered_orders:
        st.caption("Metric filter is active but no current orders fall into that bucket.")
    return visible_orders


def _get_default_order_id(orders: list[dict[str, Any]], session_key: str) -> str | None:
    if not orders:
        return None
    requested_id = str(st.session_state.get(session_key, "") or "").strip()
    if requested_id and any(item.get("mandi_order_id") == requested_id for item in orders):
        return requested_id
    return orders[0]["mandi_order_id"]


def _render_logistics_console(*, order: dict[str, Any], service, user) -> None:
    logistics = dict(order.get("logistics") or {})
    render_section_intro("Logistics Console", "Admin keeps dispatch visibility readable with transporter, vehicle, proof placeholder, and delivery notes in one place.")
    st.dataframe([logistics], use_container_width=True)
    if user.role != "platform_admin":
        return
    with st.form(f"logistics_{order.get('mandi_order_id', '')}"):
        col1, col2 = st.columns(2)
        transport_mode = col1.text_input("Transport Mode", value=str(logistics.get("transport_mode", "")))
        delivery_status = col2.text_input("Delivery Status", value=str(logistics.get("delivery_status", "")))
        driver_name = col1.text_input("Transporter / Driver", value=str(logistics.get("driver_name", "")))
        driver_mobile = col2.text_input("Driver Mobile", value=str(logistics.get("driver_mobile", "")))
        vehicle_number = col1.text_input("Vehicle Number", value=str(logistics.get("vehicle_number", "")))
        expected_delivery = col2.text_input("Expected Delivery", value=str(logistics.get("expected_delivery", "")))
        proof_url = col1.text_input("Proof Image URL", value=str(logistics.get("proof_image_url", logistics.get("proof_url", ""))))
        dispatch_note = st.text_area("Dispatch Note", value=str(logistics.get("dispatch_note", "")))
        submitted = st.form_submit_button("Save Logistics Update")
    if submitted:
        service.update_supply_logistics(
            mandi_order_id=order.get("mandi_order_id", ""),
            actor_email=user.email,
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


def render_procurement_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    service = app_context["procurement_transaction_service"]
    governance_service = app_context["governance_service"]
    page_key = f"mandi_orders_{(user.role if user else 'public')}"

    render_page_header(
        "Mandi Orders",
        "Track admin-controlled raw-material supply. Raw Materials stay in the supply layer, while Products stay in the manufacturer selling layer.",
        ["Raw Material Supply", user.role.replace("_", " ").title() if user else "Role"],
    )
    if not user:
        st.info("Sign in required.")
        return

    all_materials = governance_service.list_raw_materials()
    all_mahajans = governance_service.list_mahajans()
    materials_by_id = _index_by(all_materials, "raw_material_id")
    mahajans_by_id = _index_by(all_mahajans, "mahajan_id")
    cart_service = app_context.get("cart_service")
    image_service = app_context.get("image_service")

    if user.role == "platform_admin":
        orders = service.list_supply_orders()
        render_metric_grid(
            [
                render_metric_card("Open Requests", str(len(filter_supply_orders(orders, "OPEN_REQUESTS"))), "PENDING"),
                render_metric_card("Awaiting Mahajan Quote", str(len(filter_supply_orders(orders, "AWAITING_MAHAJAN_QUOTE"))), "OPEN"),
                render_metric_card("Awaiting Manufacturer Confirmation", str(len(filter_supply_orders(orders, "AWAITING_MANUFACTURER_CONFIRMATION"))), "WARNING"),
                render_metric_card("Closed", str(len(filter_supply_orders(orders, "CLOSED"))), "SUCCESS"),
            ]
        )
        _render_mandi_order_filters(page_key, orders)
        overview_tab, requests_tab, responses_tab, orders_tab = st.tabs(["Overview", "Requests", "Responses", "Orders"])
        with overview_tab:
            render_section_intro("Admin Supply Control", "Admin controls the full mandi supply lane: manufacturer demand, mahajan assignment, downstream pricing, ledger creation, and final closure.")
            if orders:
                default_id = _get_default_order_id(orders, "deep_link::mandi_orders")
                selected_id = st.selectbox("Review Mandi Order", [item["mandi_order_id"] for item in orders], key="admin_mandi_detail", index=[item["mandi_order_id"] for item in orders].index(default_id) if default_id else 0)
                selected = next(item for item in orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, selected.get("manufacturer_id", "")),
                )
                _render_logistics_console(order=selected, service=service, user=user)
            else:
                render_empty_state("No mandi orders are available yet.")
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            pending = [item for item in orders if item.get("status") in {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING"}]
            st.dataframe(pending, use_container_width=True)
            if pending:
                selected_id = st.selectbox("Assign Mahajan", [item["mandi_order_id"] for item in pending], key="admin_assign_supply")
                mahajans = [item for item in all_mahajans if item.get("status") == "ACTIVE"]
                if mahajans:
                    selected_mahajan = st.selectbox("Mahajan", [item["mahajan_id"] for item in mahajans], format_func=lambda item_id: f"{item_id} | {mahajans_by_id.get(item_id, {}).get('business_name', 'Supplier')}")
                    if st.button("Send To Mahajan", use_container_width=True):
                        service.assign_supply_to_mahajan(mandi_order_id=selected_id, mahajan_id=selected_mahajan, admin_email=user.email)
                        st.success("Supply request sent to mahajan.")
                        st.rerun()
                else:
                    st.info("Create and activate a mahajan before assigning supply requests.")
            else:
                st.info("No manufacturer supply requests are waiting for mahajan assignment.")
        with responses_tab:
            quoted = [item for item in orders if item.get("status") == "MAHAJAN_QUOTED"]
            st.dataframe(quoted, use_container_width=True)
            if quoted:
                selected_id = st.selectbox("Set Manufacturer Price", [item["mandi_order_id"] for item in quoted], key="admin_price_supply")
                selected = next(item for item in quoted if item["mandi_order_id"] == selected_id)
                manufacturer_price = st.number_input("Manufacturer Unit Price", min_value=0.0, step=1.0, value=float(selected.get("manufacturer_unit_price", selected.get("mahajan_unit_price", 0)) or 0))
                fee_percent = st.number_input("Mahajan Fee Percent", min_value=0.0, step=0.5, value=float((selected.get("commission_object") or {}).get("mahajan_transaction_fee_percent", 1) or 1))
                if st.button("Set Admin Price", use_container_width=True):
                    updated = service.set_manufacturer_supply_price(
                        mandi_order_id=selected_id,
                        manufacturer_unit_price=manufacturer_price,
                        admin_email=user.email,
                        mahajan_fee_percent=fee_percent,
                    )
                    st.success("Manufacturer supply price set.")
                    st.json(updated.get("commission_object", {}), expanded=False)
                    st.rerun()
            else:
                st.info("No mahajan quotes are waiting for downstream pricing.")
        with orders_tab:
            visible_orders = _render_orders_table(page_key, orders)
            if visible_orders:
                default_id = _get_default_order_id(visible_orders, "deep_link::mandi_orders")
                selected_id = st.selectbox("Mandi Order Detail", [item["mandi_order_id"] for item in visible_orders], key="admin_order_ops", index=[item["mandi_order_id"] for item in visible_orders].index(default_id) if default_id else 0)
                selected = next(item for item in visible_orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, selected.get("manufacturer_id", "")),
                )
                _render_logistics_console(order=selected, service=service, user=user)
                col1, col2 = st.columns(2)
                with col1:
                    if selected.get("status") == "MANUFACTURER_RECEIVED" and st.button("Close Order", use_container_width=True, key=f"close_{selected_id}"):
                        service.close_supply_order(mandi_order_id=selected_id, admin_email=user.email)
                        st.success("Mandi order closed.")
                        st.rerun()
                with col2:
                    if selected.get("status") not in {"CANCELLED", "CLOSED", "MANUFACTURER_RECEIVED"}:
                        reason = st.text_input("Cancel Reason", key=f"cancel_reason_{selected_id}")
                        if st.button("Cancel Order", use_container_width=True, key=f"cancel_{selected_id}"):
                            service.cancel_supply_order(mandi_order_id=selected_id, admin_email=user.email, reason=reason)
                            st.warning("Mandi order cancelled.")
                            st.rerun()
            else:
                st.info("No mandi orders are available yet.")
        return

    if user.role == "mahajan":
        mahajan = governance_service.get_mahajan_by_email(user.email)
        if not mahajan:
            st.info("Your mahajan profile is not linked yet. Ask admin to activate your supplier record.")
            return
        orders = service.list_supply_orders(mahajan_id=mahajan.get("mahajan_id"))
        render_metric_grid(
            [
                render_metric_card("Open Requests", str(len(filter_supply_orders(orders, "OPEN_REQUESTS"))), "OPEN"),
                render_metric_card("Awaiting Mahajan Quote", str(len(filter_supply_orders(orders, "AWAITING_MAHAJAN_QUOTE"))), "PENDING"),
                render_metric_card("Dispatched", str(len(filter_supply_orders(orders, "DISPATCHED"))), "SUCCESS"),
                render_metric_card("Closed", str(len(filter_supply_orders(orders, "CLOSED"))), "SUCCESS"),
            ]
        )
        _render_mandi_order_filters(page_key, orders)
        overview_tab, requests_tab, responses_tab, orders_tab = st.tabs(["Overview", "Requests", "Responses", "Orders"])
        with overview_tab:
            render_section_intro("Mahajan Supply Orders", "Mahajan works only on raw-material supply assigned by admin. Finished product selling stays outside this page.")
            if orders:
                default_id = _get_default_order_id(orders, "deep_link::mandi_orders")
                selected_id = st.selectbox("Review Assigned Supply Order", [item["mandi_order_id"] for item in orders], key="mahajan_mandi_detail", index=[item["mandi_order_id"] for item in orders].index(default_id) if default_id else 0)
                selected = next(item for item in orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=[],
                )
                st.caption(f"Deep link target: {build_deep_link_target('SUPPLY_ORDER', selected_id)['route']}")
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            awaiting = [item for item in orders if item.get("status") == "SENT_TO_MAHAJAN"]
            st.dataframe(awaiting, use_container_width=True)
            if not awaiting:
                st.info("No supply orders are waiting for your quote.")
        with responses_tab:
            quotable = [item for item in orders if item.get("status") == "SENT_TO_MAHAJAN"]
            if quotable:
                selected_id = st.selectbox("Quote Supply Order", [item["mandi_order_id"] for item in quotable], key="mahajan_quote_order")
                price = st.number_input("Mahajan Unit Price", min_value=0.0, step=1.0)
                note = st.text_area("Mahajan Quote Note")
                if st.button("Submit Quote", use_container_width=True):
                    service.quote_supply_order(
                        mandi_order_id=selected_id,
                        mahajan_id=mahajan.get("mahajan_id", ""),
                        mahajan_unit_price=price,
                        mahajan_email=user.email,
                        notes=note,
                    )
                    st.success("Quote submitted.")
                    st.rerun()
            else:
                st.info("No supply orders are waiting for a mahajan quote.")
        with orders_tab:
            visible_orders = _render_orders_table(page_key, orders)
            dispatchable = [item for item in visible_orders if item.get("status") == "MANUFACTURER_CONFIRMED"]
            if visible_orders:
                default_id = _get_default_order_id(visible_orders, "deep_link::mandi_orders")
                selected_id = st.selectbox("Assigned Order Detail", [item["mandi_order_id"] for item in visible_orders], key="mahajan_order_ops", index=[item["mandi_order_id"] for item in visible_orders].index(default_id) if default_id else 0)
                selected = next(item for item in visible_orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=[],
                )
            if dispatchable:
                selected_dispatch = st.selectbox("Dispatch Order", [item["mandi_order_id"] for item in dispatchable], key="mahajan_dispatch_order")
                if st.button("Mark Dispatched", use_container_width=True):
                    service.dispatch_supply_order(mandi_order_id=selected_dispatch, mahajan_id=mahajan.get("mahajan_id", ""), actor_email=user.email)
                    st.success("Supply order marked dispatched.")
                    st.rerun()
            else:
                st.info("No confirmed supply orders are ready for dispatch.")
        return

    if user.role in {"manufacturer", "admin_as_manufacturer"}:
        orders = service.list_supply_orders(manufacturer_code=user.manufacturer_code or "")
        materials = [item for item in all_materials if item.get("status") == "ACTIVE"]
        render_metric_grid(
            [
                render_metric_card("Open Requests", str(len(filter_supply_orders(orders, "OPEN_REQUESTS"))), "PENDING"),
                render_metric_card("Awaiting Manufacturer Confirmation", str(len(filter_supply_orders(orders, "AWAITING_MANUFACTURER_CONFIRMATION"))), "OPEN"),
                render_metric_card("Dispatched", str(len(filter_supply_orders(orders, "DISPATCHED"))), "WARNING"),
                render_metric_card("Received", str(len(filter_supply_orders(orders, "RECEIVED"))), "SUCCESS"),
            ]
        )
        _render_mandi_order_filters(page_key, orders)
        overview_tab, requests_tab, responses_tab, orders_tab = st.tabs(["Overview", "Requests", "Responses", "Orders"])
        with overview_tab:
            render_section_intro("Admin-Controlled Raw Material Supply", "Request raw materials here. Finished products that you sell through Marketplace or MandiPlace stay on the Products page.")
            if orders:
                default_id = _get_default_order_id(orders, "deep_link::mandi_orders")
                selected_id = st.selectbox("Review My Mandi Order", [item["mandi_order_id"] for item in orders], key="manufacturer_mandi_detail", index=[item["mandi_order_id"] for item in orders].index(default_id) if default_id else 0)
                selected = next(item for item in orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, user.manufacturer_code or ""),
                )
                _render_logistics_console(order=selected, service=service, user=user)
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            if not materials:
                st.info("No raw materials are available yet. Ask admin to onboard a mahajan supply catalog first.")
            else:
                preview_cards = materials[:4]
                if preview_cards:
                    columns = st.columns(min(len(preview_cards), 4))
                    for index, item in enumerate(preview_cards):
                        with columns[index % len(columns)]:
                            image = image_service.get_display_image(item, label=str(item.get("name", "Raw Material"))) if image_service else {"src": "", "alt": str(item.get("name", "Raw Material")), "status": "NONE"}
                            if render_product_card(
                                item=item,
                                variant="MANDIPLACE_PRODUCT",
                                image=image,
                                title=str(item.get("name", item.get("raw_material_id", "Raw Material"))),
                                subtitle=str(item.get("category", "RAW_MATERIAL")),
                                price_label="Supply",
                                price_value=str(item.get("supply_price", 0)),
                                availability_label=f"Qty {item.get('available_qty', 0)}",
                                visibility_label=str(item.get("status", "ACTIVE")),
                                action_label="Add To Request Cart",
                                action_key=f"mandi_add_{item.get('raw_material_id', index)}",
                            ):
                                cart_service.add_item(
                                    "manufacturer",
                                    user.manufacturer_code or "",
                                    cart_type="MANDIPLACE",
                                    item_id=str(item.get("raw_material_id", "")),
                                    qty=1,
                                )
                                st.success("Added to MandiPlace request cart.")
                                st.rerun()
                with st.form("manufacturer_supply_request"):
                    raw_material_id = st.selectbox("Raw Material", [item["raw_material_id"] for item in materials], format_func=lambda item_id: f"{item_id} | {materials_by_id.get(item_id, {}).get('name', 'Raw Material')}")
                    qty = st.number_input("Qty", min_value=1.0, step=1.0, value=1.0)
                    unit = st.text_input("Unit", value=str(materials_by_id.get(raw_material_id, {}).get("unit", "kg")))
                    notes = st.text_area("Requirement Note")
                    submitted = st.form_submit_button("Create Mandi Request")
                if submitted and raw_material_id:
                    if cart_service:
                        cart_service.add_item(
                            "manufacturer",
                            user.manufacturer_code or "",
                            cart_type="MANDIPLACE",
                            item_id=raw_material_id,
                            qty=int(qty),
                            metadata={"notes": notes},
                        )
                        st.success("Mandi request item added to cart.")
                        st.rerun()
                request_cart = cart_service.get_cart("manufacturer", user.manufacturer_code or "", "MANDIPLACE") if cart_service else {"items": []}
                if request_cart.get("items"):
                    st.dataframe(request_cart.get("items", []), use_container_width=True)
                    if st.button("Checkout Mandi Request Cart", use_container_width=True, key="mandi_checkout"):
                        created = cart_service.checkout(
                            "manufacturer",
                            user.manufacturer_code or "",
                            cart_type="MANDIPLACE",
                            checkout_context={"manufacturer_code": user.manufacturer_code or "", "requester_email": user.email},
                        )
                        st.success(f"Created {len(created)} admin-routed mandi request(s).")
                        st.rerun()
        with responses_tab:
            priced = [item for item in orders if item.get("status") == "ADMIN_PRICE_SET"]
            st.dataframe(priced, use_container_width=True)
            if priced:
                selected_id = st.selectbox("Confirm Priced Supply Order", [item["mandi_order_id"] for item in priced], key="manufacturer_confirm_supply")
                if st.button("Confirm Admin Price", use_container_width=True):
                    service.confirm_supply_order(mandi_order_id=selected_id, manufacturer_code=user.manufacturer_code or "", actor_email=user.email)
                    st.success("Supply order confirmed.")
                    st.rerun()
            else:
                st.info("No admin-priced supply orders are waiting for your confirmation.")
        with orders_tab:
            visible_orders = _render_orders_table(page_key, orders)
            if visible_orders:
                default_id = _get_default_order_id(visible_orders, "deep_link::mandi_orders")
                selected_id = st.selectbox("My Order Detail", [item["mandi_order_id"] for item in visible_orders], key="manufacturer_order_ops", index=[item["mandi_order_id"] for item in visible_orders].index(default_id) if default_id else 0)
                selected = next(item for item in visible_orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, user.manufacturer_code or ""),
                )
                _render_logistics_console(order=selected, service=service, user=user)
            receivable = [item for item in visible_orders if item.get("status") == "MAHAJAN_DISPATCHED"]
            if receivable:
                selected_receive = st.selectbox("Receive Supply Order", [item["mandi_order_id"] for item in receivable], key="manufacturer_receive_supply")
                if st.button("Mark Received", use_container_width=True):
                    service.receive_supply_order(mandi_order_id=selected_receive, manufacturer_code=user.manufacturer_code or "", actor_email=user.email)
                    st.success("Supply order marked received.")
                    st.rerun()
            else:
                st.info("No dispatched supply orders are waiting for receipt.")
        return

    st.info("Mandi orders are not available for this role.")
