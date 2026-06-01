from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_raw_materials_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    mahajan = governance_service.get_mahajan_by_email(user.email) if user and user.role == "mahajan" else None
    materials = governance_service.list_raw_materials(mahajan_id=(mahajan or {}).get("mahajan_id")) if user and user.role == "mahajan" else governance_service.list_raw_materials()
    supply_orders = app_context["procurement_transaction_service"].list_supply_orders(mahajan_id=(mahajan or {}).get("mahajan_id")) if user and user.role == "mahajan" else app_context["procurement_transaction_service"].list_supply_orders()

    render_page_header(
        "Raw Materials",
        "Manage raw-material supply in the admin-controlled mandi channel.",
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
        render_section_intro("Raw Material Supply", "Mahajans update their own supply catalog. Platform admin supervises the full upstream lane.")
        st.dataframe(materials, use_container_width=True)
    with catalog_tab:
        st.dataframe(materials, use_container_width=True)
    with add_tab:
        owner_id = (mahajan or {}).get("mahajan_id", "")
        with st.form("raw_material_form"):
            raw_material_id = st.text_input("Raw Material ID", value=f"RM{len(materials) + 1:03d}")
            name = st.text_input("Name")
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
                    "unit": unit,
                    "available_qty": int(available_qty),
                    "supply_price": float(supply_price),
                    "status": "ACTIVE",
                }
            )
            st.success("Raw material saved.")
            st.rerun()
    with activity_tab:
        st.dataframe(supply_orders, use_container_width=True)
