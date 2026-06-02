from __future__ import annotations

from typing import Any

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state
from utils.page_ui import render_metric_button_row


def is_suta_material(item: dict[str, Any]) -> bool:
    category = str(item.get("category") or "").strip().upper()
    name = str(item.get("name") or "").strip().lower()
    return category == "SUTA" or "suta" in name or "yarn" in name


def list_suta_materials(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in materials if is_suta_material(item) and item.get("status") == "ACTIVE"]


def render_suta_mandi_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    procurement_service = app_context["procurement_transaction_service"]
    page_key = "suta_mandi"

    render_page_header(
        "Suta Mandi",
        "Manufacturer-only suta purchasing market curated by admin and supplied through mahajans. This is a raw-material buying surface, not a finished-product market.",
        ["Manufacturer Only", "Admin Curated", "Mahajan Supplied"],
    )
    if not user or user.role not in {"manufacturer", "admin_as_manufacturer"}:
        st.info("Suta Mandi is available only in manufacturer workspace context.")
        return
    if not user.manufacturer_code:
        st.info("Manufacturer code is required to place a suta mandi request.")
        return

    all_materials = governance_service.list_raw_materials()
    suta_materials = list_suta_materials(all_materials)
    orders = procurement_service.list_supply_orders(manufacturer_code=user.manufacturer_code)
    suta_orders = [item for item in orders if is_suta_material(next((mat for mat in all_materials if mat.get("raw_material_id") == item.get("raw_material_id")), {}))]

    render_metric_grid(
        [
            render_metric_card("Suta Types", str(len(suta_materials)), "SUCCESS"),
            render_metric_card("Open Requests", str(len([item for item in suta_orders if item.get("status") not in {'CLOSED', 'CANCELLED', 'MANUFACTURER_RECEIVED'}])), "PENDING"),
            render_metric_card("Awaiting Quote", str(len([item for item in suta_orders if item.get("status") == 'SENT_TO_MAHAJAN'])), "OPEN"),
            render_metric_card("Price Ready", str(len([item for item in suta_orders if item.get("status") == 'ADMIN_PRICE_SET'])), "WARNING"),
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(len(suta_materials)), "tab_name": "Overview"},
            {"label": "Catalog", "value": str(len(suta_materials)), "tab_name": "Catalog"},
            {"label": "Request", "value": str(len([item for item in suta_orders if item.get('status') == 'ADMIN_PRICE_SET'])), "tab_name": "Request Suta"},
            {"label": "Orders", "value": str(len(suta_orders)), "tab_name": "My Suta Orders"},
        ],
    )
    overview_tab, catalog_tab, request_tab, orders_tab = st.tabs(["Overview", "Catalog", "Request Suta", "My Suta Orders"])
    with overview_tab:
        render_section_intro(
            "Suta Supply Market",
            "Manufacturers can browse suta varieties here and raise admin-managed mandi requests. Mahajans supply the raw material, while admin controls routing and pricing.",
        )
        if suta_materials:
            st.dataframe(suta_materials, use_container_width=True)
        else:
            render_empty_state("No suta materials are listed yet.")
    with catalog_tab:
        if not suta_materials:
            render_empty_state("No suta raw materials are listed yet. Ask admin or mahajan to onboard suta supply in Raw Materials.")
        else:
            catalog_rows = [
                {
                    "raw_material_id": item.get("raw_material_id", ""),
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "unit": item.get("unit", ""),
                    "available_qty": item.get("available_qty", 0),
                    "supply_price": item.get("supply_price", 0),
                    "mahajan_id": item.get("mahajan_id", ""),
                    "status": item.get("status", ""),
                }
                for item in suta_materials
            ]
            filtered_rows = render_filter_bar(page_key="suta_catalog", rows=catalog_rows, search_fields=["raw_material_id", "name", "mahajan_id"], status_field="status", price_field="supply_price", search_placeholder="Search suta by ID, name, or mahajan")
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_rows), file_name="suta-mandi.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_rows), file_name="suta-mandi.json", mime="application/json", use_container_width=True)
            st.dataframe(filtered_rows, use_container_width=True)
    with request_tab:
        if not suta_materials:
            st.info("No suta material is ready for requests right now.")
        else:
            with st.form("create_suta_request"):
                raw_material_id = st.selectbox(
                    "Suta Type",
                    [item["raw_material_id"] for item in suta_materials],
                    format_func=lambda material_id: f"{material_id} | {next((item.get('name', 'Suta') for item in suta_materials if item['raw_material_id'] == material_id), 'Suta')}",
                )
                selected = next(item for item in suta_materials if item["raw_material_id"] == raw_material_id)
                qty = st.number_input("Required Qty", min_value=1.0, step=1.0, value=1.0)
                unit = st.text_input("Unit", value=str(selected.get("unit", "kg")))
                notes = st.text_area("Requirement Note", placeholder="Count, blend, color, twist, cone details, or packing instructions")
                submitted = st.form_submit_button("Create Suta Request")
            if submitted:
                procurement_service.create_supply_request(
                    manufacturer_code=user.manufacturer_code,
                    raw_material_id=raw_material_id,
                    qty=qty,
                    unit=unit,
                    requested_by=user.email,
                    notes=notes,
                )
                st.success("Suta mandi request sent for admin review.")
                st.rerun()
    with orders_tab:
        render_section_intro("My Suta Orders", "Only your manufacturer suta orders appear here. Final supply still moves through admin-managed mandi flow.")
        if suta_orders:
            st.dataframe(suta_orders, use_container_width=True)
        else:
            render_empty_state("No suta mandi orders found for this manufacturer yet.")
