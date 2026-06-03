from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.entity_form import render_entity_form
from components.filter_bar import render_filter_bar
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from utils.page_ui import render_empty_state


def render_raw_materials_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    all_mahajans = governance_service.list_mahajans()
    mahajan = governance_service.get_mahajan_by_email(user.email) if user and user.role == "mahajan" else None
    materials = governance_service.list_raw_materials(mahajan_id=(mahajan or {}).get("mahajan_id")) if user and user.role == "mahajan" else governance_service.list_raw_materials()
    supply_orders = app_context["procurement_transaction_service"].list_supply_orders(mahajan_id=(mahajan or {}).get("mahajan_id")) if user and user.role == "mahajan" else app_context["procurement_transaction_service"].list_supply_orders()
    image_service = app_context.get("image_service")

    render_platform_shell(
        title="Raw Materials",
        subtitle="Manage raw-material supply in the admin-controlled mandi channel. This page is for supply inputs, not finished products.",
        badges=["Supply Network", user.role.replace("_", " ").title() if user else "Role"],
        role=user.role.replace("_", " ").title() if user else "Supply View",
        metrics=[("Catalog", str(len(materials))), ("Open Supply Orders", str(len(supply_orders)))],
        breadcrumbs=["Workspace", "Supply", "Raw Materials"],
        primary_actions=["Add Raw Material" if user and user.role in {"platform_admin", "mahajan"} else "Review Supply"],
    )
    render_kpi_cards(
        [
            {"label": "Active Raw Materials", "value": str(len([item for item in materials if item.get("status") == "ACTIVE"])), "status": "SUCCESS"},
            {"label": "Low Stock", "value": str(len([item for item in materials if int(item.get("available_qty", 0) or 0) <= 10])), "status": "WARNING"},
            {"label": "Open Admin Requests", "value": str(len([item for item in supply_orders if item.get("status") not in {'CLOSED', 'CANCELLED'}])), "status": "PENDING"},
        ]
    )
    overview_tab, catalog_tab, add_tab, activity_tab = st.tabs(["Overview", "Catalog", "Add Raw Material", "Activity"])
    with overview_tab:
        render_section_intro("Raw Material Supply", "Raw Materials belong to the mahajan/admin supply layer. Finished Products remain on the Products page for downstream selling.")
        preview = filtered_materials = render_filter_bar(
            page_key="raw_materials_overview",
            rows=materials,
            search_fields=["raw_material_id", "name", "mahajan_id", "category"],
            status_field="status",
            date_field="updated_at",
            price_field="supply_price",
            search_placeholder="Search by raw material ID, name, or mahajan",
        )
        preview_cards = preview[:3]
        if preview_cards:
            card_columns = st.columns(min(len(preview_cards), 3))
            for index, item in enumerate(preview_cards):
                with card_columns[index % len(card_columns)]:
                    image = image_service.get_display_image(item, label=str(item.get("name", "Raw Material"))) if image_service else {"src": "", "alt": str(item.get("name", "Raw Material")), "status": "NONE"}
                    render_product_card(
                        item=item,
                        variant="RAW_MATERIAL",
                        image=image,
                        title=str(item.get("name", item.get("raw_material_id", "Raw Material"))),
                        subtitle=str(item.get("category", "RAW_MATERIAL")),
                        price_label="Supply",
                        price_value=str(item.get("supply_price", 0)),
                        availability_label=f"Qty {item.get('available_qty', 0)}",
                        visibility_label=str(item.get("status", "ACTIVE")),
                        action_label="View Material",
                        action_key=f"raw_material_preview_{item.get('raw_material_id', index)}",
                    )
        if filtered_materials:
            render_data_grid(
                page_key="raw_materials_catalog",
                rows=filtered_materials,
                search_fields=["raw_material_id", "name", "mahajan_id", "category"],
                status_field="status",
                date_field="updated_at",
                price_field="supply_price",
                search_placeholder="Search by raw material ID, name, or mahajan",
            )
        else:
            render_empty_state("No Raw Materials Added")
    with catalog_tab:
        if materials:
            render_data_grid(
                page_key="raw_materials_registry",
                rows=materials,
                search_fields=["raw_material_id", "name", "mahajan_id", "category"],
                status_field="status",
                date_field="updated_at",
                price_field="supply_price",
                search_placeholder="Search by raw material ID, name, or mahajan",
            )
        else:
            render_empty_state("No Raw Materials Added")
    with add_tab:
        owner_id = (mahajan or {}).get("mahajan_id", "")
        with render_entity_form("raw_material_form", title="Create Raw Material"):
            raw_material_id = st.text_input("Raw Material ID", value=f"RM{len(materials) + 1:03d}")
            name = st.text_input("Name")
            if user and user.role == "platform_admin":
                owner_id = st.selectbox("Mahajan Owner", [item["mahajan_id"] for item in all_mahajans], format_func=lambda mahajan_id: f"{mahajan_id} | {next((item.get('business_name', '') for item in all_mahajans if item['mahajan_id'] == mahajan_id), '')}") if all_mahajans else ""
            category = st.selectbox("Category", ["RAW_MATERIAL", "SUTA", "FIBER", "DYE", "CHEMICAL"], index=0)
            unit = st.text_input("Unit", value="kg")
            description = st.text_area("Description")
            available_qty = st.number_input("Available Qty", min_value=0, step=1)
            supply_price = st.number_input("Supply Price", min_value=0.0, step=1.0)
            image_url = st.text_input("Image URL", placeholder="Optional image URL")
            image_alt_text = st.text_input("Image Alt Text", placeholder="Short image description")
            uploaded_image = st.file_uploader("Optional Raw Material Image Upload", type=["jpg", "jpeg", "png"], key="raw_material_upload")
            submitted = st.form_submit_button("Save Raw Material")
        if submitted and raw_material_id.strip() and name.strip():
            image_file_ref = image_service.save_uploaded_image_if_supported(uploaded_image, folder="raw_materials") if image_service and uploaded_image else ""
            image_metadata = image_service.normalize_image_metadata(
                image_url=image_url,
                image_file_ref=image_file_ref,
                image_alt_text=image_alt_text or name,
            ) if image_service else {"image_url": image_url}
            governance_service.upsert_raw_material(
                {
                    "raw_material_id": raw_material_id,
                    "mahajan_id": owner_id,
                    "name": name,
                    "category": category,
                    "unit": unit,
                    "description": description,
                    "available_qty": int(available_qty),
                    "supply_price": float(supply_price),
                    **image_metadata,
                    "status": "ACTIVE",
                }
            )
            st.success("Raw material saved.")
            st.rerun()
    with activity_tab:
        st.caption("Supply activity only. Finished product orders and catalog selling stay outside this page.")
        if supply_orders:
            render_data_grid(
                page_key="raw_material_supply_activity",
                rows=supply_orders,
                search_fields=["supply_order_id", "mahajan_id", "manufacturer_code", "raw_material_id"],
                status_field="status",
                date_field="updated_at",
                search_placeholder="Search by supply order, mahajan, or material ID",
            )
        else:
            render_empty_state("No Active Supply Requests")
