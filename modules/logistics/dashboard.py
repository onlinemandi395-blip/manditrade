from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_empty_state


def render_logistics_dashboard(app_context: dict) -> None:
    procurement_service = app_context["procurement_transaction_service"]
    orders = procurement_service.list_mandiplace_orders()
    logistics_rows = []
    for order in orders:
        courier = dict(order.get("courier") or {})
        logistics = dict(order.get("logistics") or {})
        logistics_rows.append(
            {
                "mandiplace_order_id": order.get("mandiplace_order_id", ""),
                "requesting_manufacturer_id": order.get("requesting_manufacturer_id", ""),
                "supplier_manufacturer_id": order.get("supplier_manufacturer_id", ""),
                "provider_name": courier.get("provider_name", ""),
                "tracking_reference": courier.get("tracking_reference", ""),
                "courier_status": courier.get("status", ""),
                "delivery_status": logistics.get("delivery_status", ""),
                "driver_name": courier.get("driver_name", logistics.get("driver_name", "")),
                "vehicle_number": courier.get("vehicle_number", logistics.get("vehicle_number", "")),
            }
        )
    in_transit = [item for item in logistics_rows if item.get("courier_status") == "IN_TRANSIT"]
    delivered = [item for item in logistics_rows if item.get("courier_status") == "DELIVERED"]
    render_page_header(
        "Logistics",
        "Track courier booking and live delivery status for admin-routed manufacturer procurement.",
        ["Platform Admin", "Logistics Tracking"],
    )
    render_metric_grid(
        [
            render_metric_card("Tracked Orders", str(len(logistics_rows)), "OPEN"),
            render_metric_card("In Transit", str(len(in_transit)), "WARNING"),
            render_metric_card("Delivered", str(len(delivered)), "SUCCESS"),
        ]
    )
    render_section_intro("MandiPlace Logistics", "Courier assignment and delivery progression stay centrally visible for admin oversight.")
    if logistics_rows:
        filtered = render_filter_bar(
            page_key="mandiplace_logistics",
            rows=logistics_rows,
            search_fields=["mandiplace_order_id", "requesting_manufacturer_id", "supplier_manufacturer_id", "provider_name", "tracking_reference"],
            status_field="courier_status",
        )
        st.dataframe(filtered, use_container_width=True)
    else:
        render_empty_state("No courier-tracked MandiPlace orders yet.")
