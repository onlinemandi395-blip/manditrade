from __future__ import annotations

from typing import Any

import streamlit as st

from components.order_timeline import render_order_timeline_component
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import get_active_filter, render_metric_button_row, render_status_chip

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
    render_section_intro("Mandi Order Detail", "Raw Materials belong to the admin/mahajan supply layer. Products remain the manufacturer selling layer.")
    render_status_chip("Current Status", MANDI_TIMELINE_LABELS.get(detail["current_status"], detail["current_status"]))
    render_status_chip("Next Action", detail["next_action"])
    render_order_timeline_component(order.get("status", ""), steps=MANDI_TIMELINE_STEPS, labels=MANDI_TIMELINE_LABELS)
    col1, col2 = st.columns(2)
    with col1:
        st.json(
            {
                "order_id": detail["order_id"],
                "manufacturer": detail["manufacturer"],
                "mahajan": detail["mahajan"],
                "raw_material_items": detail["raw_material_items"],
                "current_status": detail["current_status"],
                "next_action": detail["next_action"],
            },
            expanded=False,
        )
    with col2:
        st.json(
            {
                "mahajan_price": detail["mahajan_price"],
                "manufacturer_price": detail["manufacturer_price"],
                "admin_earning": detail["admin_earning"],
                "ledger_status": detail["ledger_status"],
            },
            expanded=False,
        )
    st.caption("Timeline")
    st.write(" -> ".join(detail["timeline"]))


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
    st.dataframe(visible_orders, use_container_width=True)
    if active_filter and not filtered_orders:
        st.info("No mandi orders match the selected dashboard card right now.")
    return visible_orders


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
                selected_id = st.selectbox("Review Mandi Order", [item["mandi_order_id"] for item in orders], key="admin_mandi_detail")
                selected = next(item for item in orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, selected.get("manufacturer_id", "")),
                )
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
                selected_id = st.selectbox("Mandi Order Detail", [item["mandi_order_id"] for item in visible_orders], key="admin_order_ops")
                selected = next(item for item in visible_orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, selected.get("manufacturer_id", "")),
                )
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
                selected_id = st.selectbox("Review Assigned Supply Order", [item["mandi_order_id"] for item in orders], key="mahajan_mandi_detail")
                selected = next(item for item in orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=[],
                )
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
                selected_id = st.selectbox("Assigned Order Detail", [item["mandi_order_id"] for item in visible_orders], key="mahajan_order_ops")
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
            render_section_intro("Admin-Controlled Raw Material Supply", "Request raw materials here. Finished products that you sell to clients or marketplace buyers stay on the Products page.")
            if orders:
                selected_id = st.selectbox("Review My Mandi Order", [item["mandi_order_id"] for item in orders], key="manufacturer_mandi_detail")
                selected = next(item for item in orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, user.manufacturer_code or ""),
                )
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            if not materials:
                st.info("No raw materials are available yet. Ask admin to onboard a mahajan supply catalog first.")
            else:
                with st.form("manufacturer_supply_request"):
                    raw_material_id = st.selectbox("Raw Material", [item["raw_material_id"] for item in materials], format_func=lambda item_id: f"{item_id} | {materials_by_id.get(item_id, {}).get('name', 'Raw Material')}")
                    qty = st.number_input("Qty", min_value=1.0, step=1.0, value=1.0)
                    unit = st.text_input("Unit", value=str(materials_by_id.get(raw_material_id, {}).get("unit", "kg")))
                    notes = st.text_area("Requirement Note")
                    submitted = st.form_submit_button("Create Mandi Request")
                if submitted and raw_material_id:
                    service.create_supply_request(
                        manufacturer_code=user.manufacturer_code or "",
                        raw_material_id=raw_material_id,
                        qty=qty,
                        unit=unit,
                        requested_by=user.email,
                        notes=notes,
                    )
                    st.success("Mandi supply request created for admin review.")
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
                selected_id = st.selectbox("My Order Detail", [item["mandi_order_id"] for item in visible_orders], key="manufacturer_order_ops")
                selected = next(item for item in visible_orders if item["mandi_order_id"] == selected_id)
                _render_supply_order_detail(
                    selected,
                    role=user.role,
                    materials_by_id=materials_by_id,
                    mahajans_by_id=mahajans_by_id,
                    supply_ledger_entries=governance_service.list_supply_ledger_entries(),
                    mandi_ledger_entries=_get_mandi_ledger_entries(service, user.manufacturer_code or ""),
                )
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
