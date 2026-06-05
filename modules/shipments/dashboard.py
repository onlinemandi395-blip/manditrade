from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from utils.page_ui import render_empty_state


def _shipment_rows(app_context: dict, user) -> list[dict]:
    governance_service = app_context["governance_service"]
    shipments = governance_service.list_shipments()
    if user.role == "platform_admin":
        return shipments
    if user.role in {"manufacturer", "admin_as_manufacturer"}:
        warehouse_ids = {
            item.get("warehouse_id")
            for item in governance_service.list_warehouses(owner_role="manufacturer", owner_id=user.manufacturer_code or "")
        }
        manufacturer_code = user.manufacturer_code or ""
        return [
            item
            for item in shipments
            if item.get("source_warehouse_id") in warehouse_ids
            or item.get("manufacturer_code") == manufacturer_code
            or item.get("requesting_manufacturer_id") == manufacturer_code
            or item.get("supplier_manufacturer_id") == manufacturer_code
            or item.get("manufacturer_id") == manufacturer_code
        ]
    if user.role == "mahajan":
        mahajan = governance_service.get_mahajan_by_email(user.email)
        warehouse_ids = {
            item.get("warehouse_id")
            for item in governance_service.list_warehouses(owner_role="mahajan", owner_id=(mahajan or {}).get("mahajan_id", ""))
        }
        mahajan_id = (mahajan or {}).get("mahajan_id", "")
        return [item for item in shipments if item.get("source_warehouse_id") in warehouse_ids or item.get("mahajan_id") == mahajan_id]
    return []


def render_shipments_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    shipments = _shipment_rows(app_context, user)
    warehouse_index = {item.get("warehouse_id"): item for item in governance_service.list_warehouses()}
    source_index = {
        item.get("source_id", ""): item
        for item in governance_service.list_procurement_sources(include_legacy=True)
        if item.get("source_id")
    }
    rows = []
    for shipment in shipments:
        warehouse = warehouse_index.get(shipment.get("source_warehouse_id"), {})
        manufacturer_code = str(shipment.get("manufacturer_code") or shipment.get("supplier_manufacturer_id") or "").strip().upper()
        mahajan_id = str(shipment.get("mahajan_id") or "").strip().upper()
        derived_source_id = str(shipment.get("source_id") or "").strip().upper()
        if not derived_source_id and manufacturer_code:
            derived_source_id = f"MANU-{manufacturer_code}"
        if not derived_source_id and mahajan_id:
            derived_source_id = f"MAHAJAN-{mahajan_id}"
        source = source_index.get(derived_source_id, {})
        rows.append(
            {
                **shipment,
                "source_id": derived_source_id,
                "source_name": source.get("business_name", shipment.get("manufacturer_code", shipment.get("mahajan_id", ""))),
                "source_city": source.get("city", warehouse.get("city", "")),
                "source_state": source.get("state", warehouse.get("state", "")),
                "source_warehouse_name": warehouse.get("warehouse_name", shipment.get("source_warehouse_id", "")),
            }
        )
    render_platform_shell(
        title="Shipments",
        subtitle="Track shipment records across marketplace, procurement, and sourcing lanes with procurement source origin shown first and warehouse detail kept only as a compatibility reference.",
        badges=["Shipment Registry", "Source Origin First", user.role.replace("_", " ").title()],
        role=user.role.replace("_", " ").title(),
        metrics=[("Shipments", str(len(rows))), ("In Transit", str(len([item for item in rows if item.get("status") == "IN_TRANSIT"])))],
        breadcrumbs=["Workspace", "Logistics", "Shipments"],
        primary_actions=["Review Shipment Status"],
    )
    render_kpi_cards(
        [
            {"label": "Active Shipments", "value": str(len([item for item in rows if item.get("status") not in {'DELIVERED', 'CANCELLED'}])), "status": "OPEN"},
            {"label": "In Transit", "value": str(len([item for item in rows if item.get("status") == "IN_TRANSIT"])), "status": "WARNING"},
            {"label": "Delivered", "value": str(len([item for item in rows if item.get("status") == "DELIVERED"])), "status": "SUCCESS"},
        ]
    )
    render_section_intro("Shipment Registry", "Each shipment now links an order flow to a procurement source first, with warehouse detail retained only where legacy inventory flows still need it.")
    if rows:
        render_data_grid(
            page_key="shipments_registry",
            rows=rows,
            search_fields=["shipment_id", "order_id", "shipment_type", "source_name", "source_id", "destination_city", "tracking_number"],
            status_field="status",
            date_field="updated_at",
            search_placeholder="Search shipment, order, source, or tracking number",
        )
    else:
        render_empty_state("No shipments recorded yet.")
