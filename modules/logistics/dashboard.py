from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.filter_bar import render_filter_bar
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from utils.page_ui import render_empty_state


def render_logistics_dashboard(app_context: dict) -> None:
    procurement_service = app_context["procurement_transaction_service"]
    governance_service = app_context["governance_service"]
    orders = procurement_service.list_mandiplace_orders()
    shipments = governance_service.list_shipments()
    warehouses = governance_service.list_warehouses()
    courier_services = governance_service.list_courier_services()
    logistics_rows = []
    for shipment in shipments:
        order = next((item for item in orders if item.get("mandiplace_order_id") == shipment.get("order_id")), {})
        courier = dict(order.get("courier") or {})
        logistics = dict(order.get("logistics") or {})
        warehouse = governance_service.get_warehouse(shipment.get("source_warehouse_id", "")) or {}
        logistics_rows.append(
            {
                "shipment_id": shipment.get("shipment_id", ""),
                "order_id": shipment.get("order_id", ""),
                "shipment_type": shipment.get("shipment_type", ""),
                "requesting_manufacturer_id": order.get("requesting_manufacturer_id", ""),
                "supplier_manufacturer_id": order.get("supplier_manufacturer_id", ""),
                "source_warehouse": warehouse.get("warehouse_name", shipment.get("source_warehouse_id", "")),
                "provider_name": courier.get("provider_name", ""),
                "tracking_reference": shipment.get("tracking_number", courier.get("tracking_reference", "")),
                "courier_status": shipment.get("status", courier.get("status", "")),
                "delivery_status": logistics.get("delivery_status", shipment.get("status", "")),
                "driver_name": courier.get("driver_name", logistics.get("driver_name", "")),
                "vehicle_number": courier.get("vehicle_number", logistics.get("vehicle_number", "")),
            }
        )
    in_transit = [item for item in logistics_rows if item.get("courier_status") == "IN_TRANSIT"]
    delivered = [item for item in logistics_rows if item.get("courier_status") == "DELIVERED"]
    render_platform_shell(
        title="Logistics",
        subtitle="Track warehouses, shipments, and courier-linked delivery status across the admin-routed commerce network.",
        badges=["Platform Admin", "Logistics Tracking"],
        role="Platform Admin",
        metrics=[("Tracked Shipments", str(len(logistics_rows))), ("Transit", str(len(in_transit)))],
        breadcrumbs=["Workspace", "Operations", "Logistics"],
        primary_actions=["Track Deliveries"],
    )
    render_kpi_cards(
        [
            {"label": "Active Warehouses", "value": str(len([item for item in warehouses if item.get("status") == "ACTIVE"])), "status": "OPEN"},
            {"label": "Active Couriers", "value": str(len([item for item in courier_services if item.get("status") == "ACTIVE"])), "status": "SUCCESS"},
            {"label": "Tracked Shipments", "value": str(len(logistics_rows)), "status": "OPEN"},
            {"label": "In Transit", "value": str(len(in_transit)), "status": "WARNING"},
            {"label": "Delivered", "value": str(len(delivered)), "status": "SUCCESS"},
        ]
    )
    render_section_intro("Logistics Control", "Warehouse-linked shipments and courier progression now stay centrally visible for admin oversight.")
    if logistics_rows:
        filtered = render_filter_bar(
            page_key="mandiplace_logistics",
            rows=logistics_rows,
            search_fields=["shipment_id", "order_id", "requesting_manufacturer_id", "supplier_manufacturer_id", "source_warehouse", "provider_name", "tracking_reference"],
            status_field="courier_status",
        )
        render_data_grid(
            page_key="mandiplace_logistics_grid",
            rows=filtered,
            search_fields=["shipment_id", "order_id", "requesting_manufacturer_id", "supplier_manufacturer_id", "source_warehouse", "provider_name", "tracking_reference"],
            status_field="courier_status",
            search_placeholder="Search by shipment, order, warehouse, provider, or tracking reference",
        )
    else:
        render_empty_state("No courier-tracked MandiPlace orders yet.")
