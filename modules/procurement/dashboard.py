from __future__ import annotations

from typing import Any

import streamlit as st

from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.filter_bar import render_filter_bar
from components.order_detail_view import build_order_detail_payload, render_order_detail_view
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from components.ui_shell import render_metric_card
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

MANDIPLACE_TIMELINE_STEPS = [
    "REQUESTED_BY_MANUFACTURER",
    "ADMIN_REVIEWING",
    "SUPPLIER_ASSIGNED",
    "SUPPLIER_QUOTED",
    "ADMIN_PRICE_SET",
    "PACKAGING_SELECTED",
    "COURIER_BOOKED",
    "MANUFACTURER_CONFIRMED",
    "SUPPLIER_DISPATCHED",
    "IN_TRANSIT",
    "DELIVERED",
    "RECEIVED",
    "CLOSED",
]

MANDIPLACE_TIMELINE_LABELS = {
    "REQUESTED_BY_MANUFACTURER": "Manufacturer Requested",
    "ADMIN_REVIEWING": "Admin Reviewing",
    "SUPPLIER_ASSIGNED": "Supplier Assigned",
    "SUPPLIER_QUOTED": "Supplier Quoted",
    "ADMIN_PRICE_SET": "Admin Price Set",
    "PACKAGING_SELECTED": "Packaging Selected",
    "COURIER_BOOKED": "Courier Booked",
    "MANUFACTURER_CONFIRMED": "Manufacturer Confirmed",
    "SUPPLIER_DISPATCHED": "Supplier Dispatched",
    "IN_TRANSIT": "In Transit",
    "DELIVERED": "Delivered",
    "RECEIVED": "Received",
    "CLOSED": "Closed",
    "CANCELLED": "Cancelled",
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


def _render_logistics_console(*, order: dict[str, Any], service, user, form_scope: str = "default") -> None:
    logistics = dict(order.get("logistics") or {})
    render_section_intro("Logistics Console", "Admin keeps dispatch visibility readable with transporter, vehicle, proof placeholder, and delivery notes in one place.")
    st.dataframe([logistics], use_container_width=True)
    if user.role != "platform_admin":
        return
    form_key = f"logistics_{form_scope}_{order.get('mandi_order_id', '')}"
    with st.form(form_key):
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


def get_mandiplace_order_role_actions(role: str, order: dict[str, Any] | None, *, manufacturer_code: str = "") -> list[str]:
    if not order:
        return []
    status = str(order.get("status") or "")
    if role == "platform_admin":
        if status in {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING"}:
            return ["Assign Supplier"]
        if status == "SUPPLIER_QUOTED":
            return ["Set Price"]
        if status in {"ADMIN_PRICE_SET", "PACKAGING_SELECTED"}:
            return ["Book Courier"]
        if status == "RECEIVED":
            return ["Close Order"]
        return []
    if role in {"manufacturer", "admin_as_manufacturer"}:
        requester = str(order.get("requesting_manufacturer_id") or "")
        supplier = str(order.get("supplier_manufacturer_id") or "")
        if manufacturer_code == supplier:
            if status == "SUPPLIER_ASSIGNED":
                return ["Submit Quote"]
            if status == "MANUFACTURER_CONFIRMED":
                return ["Dispatch Order"]
        if manufacturer_code == requester:
            if status == "COURIER_BOOKED":
                return ["Confirm Price"]
            if status == "DELIVERED":
                return ["Mark Received"]
        return []
    return []


def _render_mandiplace_detail(order: dict[str, Any], *, manufacturer_code: str = "") -> None:
    items = [
        {
            "name": item.get("name", item.get("product_id", "Product")),
            "qty": item.get("qty", 0),
            "unit": item.get("unit", ""),
            "unit_price": order.get("manufacturer_unit_price", 0),
            "subtotal": float(item.get("qty", 0) or 0) * float(order.get("manufacturer_unit_price", 0) or 0),
            "thumbnail_url": "",
            "image_url": "",
        }
        for item in order.get("items", [])
    ]
    next_action = get_mandiplace_order_role_actions(
        "manufacturer" if manufacturer_code else "platform_admin",
        order,
        manufacturer_code=manufacturer_code,
    )
    render_order_detail_view(
        build_order_detail_payload(
            order,
            order_id_key="mandiplace_order_id",
            status=str(order.get("status", "")),
            items=items,
            timeline_steps=MANDIPLACE_TIMELINE_STEPS,
            timeline_labels=MANDIPLACE_TIMELINE_LABELS,
            status_history=list(order.get("internal_status_history", [])),
            logistics=dict(order.get("logistics", {})),
            payment={
                "payment_receiver": order.get("payment_receiver", ""),
                "payment_proof_url": order.get("payment_proof_url", ""),
                "payment_verified_by": order.get("payment_verified_by", ""),
                "payment_verified_at": order.get("payment_verified_at", ""),
                "cost_breakdown": dict(order.get("cost_breakdown") or {}),
                "packaging": dict(order.get("packaging") or {}),
                "courier": dict(order.get("courier") or {}),
                "commission": dict(order.get("commission") or {}),
            },
            next_action=next_action[0] if next_action else "Waiting on another role",
            trust_badges=[],
        )
    )


def _render_mandiplace_admin(app_context: dict, user, service) -> None:
    governance_service = app_context["governance_service"]
    orders = service.list_mandiplace_orders()
    packaging_services = [item for item in governance_service.list_packaging_services() if item.get("status") == "ACTIVE"]
    courier_services = [item for item in governance_service.list_courier_services() if item.get("status") == "ACTIVE"]
    render_platform_shell(
        title="MandiPlace",
        subtitle="Admin-routed manufacturer procurement keeps supplier assignment, packaging, courier, and downstream pricing under controlled review.",
        badges=["Platform Admin", "Co-Manufacturer Routing"],
        breadcrumbs=["Platform", "Mandi Network", "MandiPlace"],
        primary_actions=["Assign Supplier", "Set Final Price", "Book Courier"],
    )
    render_kpi_cards(
        [
            {"label": "Open Requests", "value": str(len([item for item in orders if item.get("status") in {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING"}])), "status": "PENDING"},
            {"label": "Assigned", "value": str(len([item for item in orders if item.get("status") == "SUPPLIER_ASSIGNED"])), "status": "OPEN"},
            {"label": "In Transit", "value": str(len([item for item in orders if item.get("status") == "IN_TRANSIT"])), "status": "WARNING"},
            {"label": "Closed", "value": str(len([item for item in orders if item.get("status") == "CLOSED"])), "status": "SUCCESS"},
        ]
    )
    overview_tab, assign_tab, pricing_tab, orders_tab = st.tabs(["Overview", "Assign Supplier", "Pricing & Logistics", "Orders"])
    with overview_tab:
        render_section_intro("Manufacturer Procurement Control", "Manufacturers request products through admin. Supplier co-manufacturer assignment, packaging, courier, and closing stay controlled here.")
        if orders:
            selected_id = st.selectbox("Review MandiPlace Order", [item["mandiplace_order_id"] for item in orders], key="mandiplace_admin_detail")
            selected = next(item for item in orders if item["mandiplace_order_id"] == selected_id)
            _render_mandiplace_detail(selected)
        st.dataframe(orders, use_container_width=True)
    with assign_tab:
        pending = [item for item in orders if item.get("status") in {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING"}]
        if pending:
            selected_id = st.selectbox("Order To Assign", [item["mandiplace_order_id"] for item in pending], key="assign_manufacturer_supplier")
            candidates = service.list_eligible_manufacturer_suppliers(mandiplace_order_id=selected_id)
            if candidates:
                st.dataframe(candidates, use_container_width=True)
                selected_supplier = st.selectbox("Eligible Supplier", [item["manufacturer_code"] for item in candidates], format_func=lambda code: f"{code} | {next((row.get('business_name', '') for row in candidates if row['manufacturer_code'] == code), '')}")
                if st.button("Assign Supplier", use_container_width=True):
                    service.assign_manufacturer_supplier(mandiplace_order_id=selected_id, supplier_manufacturer_id=selected_supplier, admin_email=user.email)
                    st.success("Supplier assigned.")
                    st.rerun()
            else:
                st.info("No eligible co-manufacturer suppliers are available for this request yet.")
        else:
            st.info("No manufacturer procurement requests are waiting for assignment.")
    with pricing_tab:
        quoted = [item for item in orders if item.get("status") in {"SUPPLIER_QUOTED", "ADMIN_PRICE_SET", "PACKAGING_SELECTED"}]
        if quoted:
            selected_id = st.selectbox("Manage Pricing", [item["mandiplace_order_id"] for item in quoted], key="manage_mandiplace_price")
            selected = next(item for item in quoted if item["mandiplace_order_id"] == selected_id)
            manufacturer_price = st.number_input("Manufacturer Unit Price", min_value=0.0, step=1.0, value=float(selected.get("manufacturer_unit_price", selected.get("supplier_unit_price", 0)) or 0))
            if st.button("Set Final Price", use_container_width=True):
                service.set_mandiplace_manufacturer_price(mandiplace_order_id=selected_id, manufacturer_unit_price=manufacturer_price, admin_email=user.email)
                st.success("Manufacturer-facing price updated.")
                st.rerun()
            if packaging_services:
                packaging_id = st.selectbox("Packaging Service", [item["packaging_service_id"] for item in packaging_services], key="mandiplace_packaging_service")
                packaging_qty = st.number_input("Packaging Qty", min_value=0.0, step=1.0, value=float((selected.get("packaging") or {}).get("qty", 1) or 1))
                if st.button("Apply Packaging", use_container_width=True):
                    service.apply_packaging_to_mandiplace_order(mandiplace_order_id=selected_id, packaging_service_id=packaging_id, qty=packaging_qty, actor_email=user.email)
                    st.success("Packaging applied.")
                    st.rerun()
            if courier_services:
                courier_id = st.selectbox("Courier Service", [item["courier_service_id"] for item in courier_services], key="mandiplace_courier_service")
                pickup = st.text_input("Pickup Location", value=str((selected.get("courier") or {}).get("pickup_location", "")))
                delivery = st.text_input("Delivery Location", value=str((selected.get("courier") or {}).get("delivery_location", "")))
                distance = st.number_input("Distance KM", min_value=0.0, step=1.0, value=float((selected.get("courier") or {}).get("distance_km", 0) or 0))
                weight = st.number_input("Weight KG", min_value=0.0, step=1.0, value=float((selected.get("courier") or {}).get("weight_kg", 0) or 0))
                if st.button("Book Courier", use_container_width=True):
                    service.book_courier_for_mandiplace_order(
                        mandiplace_order_id=selected_id,
                        courier_service_id=courier_id,
                        pickup_location=pickup,
                        delivery_location=delivery,
                        distance_km=distance,
                        weight_kg=weight,
                        actor_email=user.email,
                    )
                    st.success("Courier booked.")
                    st.rerun()
        else:
            st.info("No quoted or priceable MandiPlace orders are available right now.")
    with orders_tab:
        if orders:
            selected_id = st.selectbox("Order Detail", [item["mandiplace_order_id"] for item in orders], key="mandiplace_admin_orders")
            selected = next(item for item in orders if item["mandiplace_order_id"] == selected_id)
            _render_mandiplace_detail(selected)
            if selected.get("status") == "RECEIVED" and st.button("Close Order", use_container_width=True, key=f"close_mpo_{selected_id}"):
                service.close_mandiplace_order(mandiplace_order_id=selected_id, admin_email=user.email)
                st.success("MandiPlace order closed.")
                st.rerun()
            st.dataframe(orders, use_container_width=True)
        else:
            render_empty_state("No manufacturer procurement orders yet.")


def _render_mandiplace_manufacturer(app_context: dict, user, service) -> None:
    products = [
        item
        for item in app_context["product_catalog_service"].list_products(viewer_role="manufacturer", viewer_code=user.manufacturer_code or "")
        if item.get("status") == "ACTIVE" and item.get("available_for_mandi_network", True)
    ]
    orders = service.list_mandiplace_orders(manufacturer_code=user.manufacturer_code or "")
    render_platform_shell(
        title="MandiPlace",
        subtitle="Request co-manufacturer procurement through admin. Supplier discovery remains admin-routed, not direct.",
        badges=["Manufacturer", "Admin-Routed Procurement"],
        breadcrumbs=["Workspace", "Mandi Network", "MandiPlace"],
        primary_actions=["Create Request", "Confirm Order", "Dispatch Order"],
    )
    render_kpi_cards(
        [
            {"label": "My Requests", "value": str(len([item for item in orders if item.get("requesting_manufacturer_id") == (user.manufacturer_code or "")])), "status": "OPEN"},
            {"label": "Assigned To Me", "value": str(len([item for item in orders if item.get("supplier_manufacturer_id") == (user.manufacturer_code or "")])), "status": "PENDING"},
            {"label": "Awaiting My Confirmation", "value": str(len([item for item in orders if item.get("requesting_manufacturer_id") == (user.manufacturer_code or "") and item.get("status") == "COURIER_BOOKED"])), "status": "WARNING"},
            {"label": "In Transit", "value": str(len([item for item in orders if item.get("status") == "IN_TRANSIT"])), "status": "WARNING"},
        ]
    )
    overview_tab, request_tab, responses_tab, orders_tab = st.tabs(["Overview", "Create Request", "Actions", "Orders"])
    with overview_tab:
        render_section_intro("Admin-Routed Manufacturer Procurement", "You can request MandiPlace products here, but supplier manufacturer assignment stays under admin control.")
        if orders:
            selected_id = st.selectbox("Review Order", [item["mandiplace_order_id"] for item in orders], key="mandiplace_manufacturer_detail")
            selected = next(item for item in orders if item["mandiplace_order_id"] == selected_id)
            _render_mandiplace_detail(selected, manufacturer_code=user.manufacturer_code or "")
        st.dataframe(orders, use_container_width=True)
    with request_tab:
        if products:
            product_id = st.selectbox("Product", [item["product_id"] for item in products], format_func=lambda pid: f"{pid} | {next((row.get('name', '') for row in products if row['product_id'] == pid), '')}")
            selected_product = next(item for item in products if item["product_id"] == product_id)
            qty = st.number_input("Qty", min_value=1.0, step=1.0, value=1.0)
            requested_location = st.text_input("Requested Location")
            required_by_date = st.text_input("Required By Date")
            note = st.text_area("Request Note")
            if st.button("Create MandiPlace Request", use_container_width=True):
                service.create_mandiplace_request(
                    requesting_manufacturer_id=user.manufacturer_code or "",
                    requested_by=user.email,
                    notes=note,
                    items=[
                        {
                            "product_id": product_id,
                            "name": selected_product.get("name", product_id),
                            "qty": qty,
                            "unit": selected_product.get("unit", "unit"),
                            "requested_location": requested_location,
                            "required_by_date": required_by_date,
                        }
                    ],
                )
                st.success("MandiPlace request sent to admin.")
                st.rerun()
        else:
            st.info("No active MandiPlace products are available right now.")
    with responses_tab:
        as_supplier = [item for item in orders if item.get("supplier_manufacturer_id") == (user.manufacturer_code or "")]
        as_requester = [item for item in orders if item.get("requesting_manufacturer_id") == (user.manufacturer_code or "")]
        quote_ready = [item for item in as_supplier if item.get("status") == "SUPPLIER_ASSIGNED"]
        if quote_ready:
            selected_id = st.selectbox("Quote Assigned Order", [item["mandiplace_order_id"] for item in quote_ready], key="supplier_quote_mpo")
            supplier_price = st.number_input("Supplier Unit Price", min_value=0.0, step=1.0)
            note = st.text_area("Supplier Note")
            if st.button("Submit Supplier Quote", use_container_width=True):
                service.supplier_quote_mandiplace_order(
                    mandiplace_order_id=selected_id,
                    supplier_manufacturer_id=user.manufacturer_code or "",
                    supplier_unit_price=supplier_price,
                    actor_email=user.email,
                    notes=note,
                )
                st.success("Supplier quote submitted.")
                st.rerun()
        confirm_ready = [item for item in as_requester if item.get("status") == "COURIER_BOOKED"]
        if confirm_ready:
            selected_id = st.selectbox("Confirm Final Price", [item["mandiplace_order_id"] for item in confirm_ready], key="confirm_mpo")
            if st.button("Confirm Procurement Order", use_container_width=True):
                service.confirm_mandiplace_order(mandiplace_order_id=selected_id, manufacturer_code=user.manufacturer_code or "", actor_email=user.email)
                st.success("MandiPlace order confirmed.")
                st.rerun()
        dispatch_ready = [item for item in as_supplier if item.get("status") == "MANUFACTURER_CONFIRMED"]
        if dispatch_ready:
            selected_id = st.selectbox("Dispatch Order", [item["mandiplace_order_id"] for item in dispatch_ready], key="dispatch_mpo")
            if st.button("Mark Supplier Dispatch", use_container_width=True):
                service.dispatch_mandiplace_order(mandiplace_order_id=selected_id, supplier_manufacturer_id=user.manufacturer_code or "", actor_email=user.email)
                st.success("MandiPlace order dispatched.")
                st.rerun()
        receive_ready = [item for item in as_requester if item.get("status") == "DELIVERED"]
        if receive_ready:
            selected_id = st.selectbox("Receive Delivered Order", [item["mandiplace_order_id"] for item in receive_ready], key="receive_mpo")
            if st.button("Mark Received", use_container_width=True):
                service.receive_mandiplace_order(mandiplace_order_id=selected_id, manufacturer_code=user.manufacturer_code or "", actor_email=user.email)
                st.success("MandiPlace order received.")
                st.rerun()
        if not any([quote_ready, confirm_ready, dispatch_ready, receive_ready]):
            st.info("No MandiPlace actions are waiting on your role right now.")
    with orders_tab:
        if orders:
            st.dataframe(orders, use_container_width=True)
        else:
            render_empty_state("No MandiPlace orders available yet.")


def render_procurement_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    service = app_context["procurement_transaction_service"]
    governance_service = app_context["governance_service"]
    page_key = f"mandi_orders_{(user.role if user else 'public')}"
    active_navigation = app_context["session_state_service"].get_navigation("Dashboard")

    if not user:
        st.info("Sign in required.")
        return

    if active_navigation == "MandiPlace":
        if user.role == "platform_admin":
            _render_mandiplace_admin(app_context, user, service)
            return
        if user.role in {"manufacturer", "admin_as_manufacturer"}:
            _render_mandiplace_manufacturer(app_context, user, service)
            return
        st.info("MandiPlace procurement is available for admin and manufacturers only.")
        return

    render_platform_shell(
        title="Mandi Orders",
        subtitle="Track admin-controlled raw-material supply. Raw Materials stay in the supply layer, while Products stay in the manufacturer selling layer.",
        badges=["Raw Material Supply", user.role.replace("_", " ").title() if user else "Role"],
        role=user.role.replace("_", " ").title() if user else None,
        breadcrumbs=["Workspace", "Supply Network", "Mandi Orders"],
    )

    all_materials = governance_service.list_raw_materials()
    all_mahajans = governance_service.list_mahajans()
    materials_by_id = _index_by(all_materials, "raw_material_id")
    mahajans_by_id = _index_by(all_mahajans, "mahajan_id")
    cart_service = app_context.get("cart_service")
    image_service = app_context.get("image_service")
    trust_badge_service = app_context.get("trust_badge_service")

    if user.role == "platform_admin":
        orders = service.list_supply_orders()
        render_kpi_cards(
            [
                {"label": "Open Requests", "value": str(len(filter_supply_orders(orders, "OPEN_REQUESTS"))), "status": "PENDING"},
                {"label": "Awaiting Mahajan Quote", "value": str(len(filter_supply_orders(orders, "AWAITING_MAHAJAN_QUOTE"))), "status": "OPEN"},
                {"label": "Awaiting Manufacturer Confirmation", "value": str(len(filter_supply_orders(orders, "AWAITING_MANUFACTURER_CONFIRMATION"))), "status": "WARNING"},
                {"label": "Closed", "value": str(len(filter_supply_orders(orders, "CLOSED"))), "status": "SUCCESS"},
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
                _render_logistics_console(order=selected, service=service, user=user, form_scope="admin_overview")
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
                _render_logistics_console(order=selected, service=service, user=user, form_scope="admin_orders")
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
                _render_logistics_console(order=selected, service=service, user=user, form_scope="manufacturer_overview")
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
                                badges=trust_badge_service.badges_for_raw_material(item) if trust_badge_service else [],
                                supporting_text=str(item.get("description", "") or "Admin-routed procurement supply."),
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
                _render_logistics_console(order=selected, service=service, user=user, form_scope="manufacturer_orders")
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
