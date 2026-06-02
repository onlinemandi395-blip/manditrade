from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state


def render_raw_materials_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    all_mahajans = governance_service.list_mahajans()
    mahajan = governance_service.get_mahajan_by_email(user.email) if user and user.role == "mahajan" else None
    materials = governance_service.list_raw_materials(mahajan_id=(mahajan or {}).get("mahajan_id")) if user and user.role == "mahajan" else governance_service.list_raw_materials()
    supply_orders = app_context["procurement_transaction_service"].list_supply_orders(mahajan_id=(mahajan or {}).get("mahajan_id")) if user and user.role == "mahajan" else app_context["procurement_transaction_service"].list_supply_orders()

    render_page_header(
        "Raw Materials",
        "Manage raw-material supply in the admin-controlled mandi channel. This page is for supply inputs, not finished products.",
        ["Supply Network", user.role.replace("_", " ").title() if user else "Role"],
    )
    render_metric_grid(
        [
            render_metric_card("Active Raw Materials", str(len([item for item in materials if item.get("status") == "ACTIVE"])), "SUCCESS"),
            render_metric_card("Low Stock", str(len([item for item in materials if int(item.get("available_qty", 0) or 0) <= 10])), "WARNING"),
            render_metric_card("Open Admin Requests", str(len([item for item in supply_orders if item.get("status") not in {'CLOSED', 'CANCELLED'}])), "PENDING"),
        ]
    )
    overview_tab, catalog_tab, add_tab, activity_tab = st.tabs(["Overview", "Catalog", "Add Raw Material", "Activity"])
    with overview_tab:
        render_section_intro("Raw Material Supply", "Raw Materials belong to the mahajan/admin supply layer. Finished Products remain on the Products page for downstream selling.")
        filtered_materials = render_filter_bar(
            page_key="raw_materials_overview",
            rows=materials,
            search_fields=["raw_material_id", "name", "mahajan_id", "category"],
            status_field="status",
            date_field="updated_at",
            price_field="supply_price",
            search_placeholder="Search by raw material ID, name, or mahajan",
        )
        if filtered_materials:
            csv_col, json_col = st.columns(2)
            csv_col.download_button("Export CSV", export_rows_to_csv_bytes(filtered_materials), file_name="raw-materials.csv", mime="text/csv", use_container_width=True)
            json_col.download_button("Export JSON", export_rows_to_json_bytes(filtered_materials), file_name="raw-materials.json", mime="application/json", use_container_width=True)
            st.dataframe(filtered_materials, use_container_width=True)
        else:
            render_empty_state("No Raw Materials Added")
    with catalog_tab:
        if materials:
            st.dataframe(materials, use_container_width=True)
        else:
            render_empty_state("No Raw Materials Added")
    with add_tab:
        owner_id = (mahajan or {}).get("mahajan_id", "")
        with st.form("raw_material_form"):
            raw_material_id = st.text_input("Raw Material ID", value=f"RM{len(materials) + 1:03d}")
            name = st.text_input("Name")
            if user and user.role == "platform_admin":
                owner_id = st.selectbox("Mahajan Owner", [item["mahajan_id"] for item in all_mahajans], format_func=lambda mahajan_id: f"{mahajan_id} | {next((item.get('business_name', '') for item in all_mahajans if item['mahajan_id'] == mahajan_id), '')}") if all_mahajans else ""
            category = st.selectbox("Category", ["RAW_MATERIAL", "SUTA", "FIBER", "DYE", "CHEMICAL"], index=0)
            unit = st.text_input("Unit", value="kg")
            available_qty = st.number_input("Available Qty", min_value=0, step=1)
            supply_price = st.number_input("Supply Price", min_value=0.0, step=1.0)
            submitted = st.form_submit_button("Save Raw Material")
        if submitted and raw_material_id.strip() and name.strip():
            governance_service.upsert_raw_material(
                {
                    "raw_material_id": raw_material_id,
                    "mahajan_id": owner_id,
                    "name": name,
                    "category": category,
                    "unit": unit,
                    "available_qty": int(available_qty),
                    "supply_price": float(supply_price),
                    "status": "ACTIVE",
                }
            )
            st.success("Raw material saved.")
            st.rerun()
    with activity_tab:
        st.caption("Supply activity only. Finished product orders and catalog selling stay outside this page.")
        if supply_orders:
            st.dataframe(supply_orders, use_container_width=True)
        else:
            render_empty_state("No Active Supply Requests")
