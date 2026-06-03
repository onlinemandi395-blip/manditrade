from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_empty_state


def render_packaging_services_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    services = governance_service.list_packaging_services()
    active = [item for item in services if item.get("status") == "ACTIVE"]
    render_page_header(
        "Packaging Services",
        "Admin maintains packaging rate cards for manufacturer procurement orders without exposing direct supplier bypass.",
        ["Platform Admin", "Service Catalog"],
    )
    render_metric_grid(
        [
            render_metric_card("Total Services", str(len(services)), "OPEN"),
            render_metric_card("Active", str(len(active)), "SUCCESS"),
            render_metric_card("Archived", str(len([item for item in services if item.get('status') == 'ARCHIVED'])), "WARNING"),
        ]
    )
    overview_tab, create_tab, manage_tab = st.tabs(["Overview", "Create", "Manage"])
    with overview_tab:
        render_section_intro("Packaging Catalog", "Packaging is admin-managed and can be attached to MandiPlace procurement without changing role boundaries.")
        if services:
            filtered = render_filter_bar(
                page_key="packaging_services",
                rows=services,
                search_fields=["packaging_service_id", "name", "material_type"],
                status_field="status",
                date_field="updated_at",
            )
            st.dataframe(filtered, use_container_width=True)
        else:
            render_empty_state("No packaging services added yet.")
    with create_tab:
        with st.form("create_packaging_service"):
            service_id = st.text_input("Packaging Service ID", value=f"PKG-{len(services)+1:04d}")
            name = st.text_input("Name")
            material_type = st.selectbox("Material Type", ["BOX", "BAG", "WRAP", "CRATE", "CUSTOM"])
            unit = st.text_input("Unit", value="piece")
            base_price = st.number_input("Base Price", min_value=0.0, step=1.0)
            price_per_unit = st.number_input("Price Per Unit", min_value=0.0, step=1.0)
            minimum_charge = st.number_input("Minimum Charge", min_value=0.0, step=1.0)
            categories = st.text_input("Applicable Categories", placeholder="Rice, Wheat, Yarn")
            status = st.selectbox("Status", ["ACTIVE", "INACTIVE", "ARCHIVED"])
            submitted = st.form_submit_button("Save Packaging Service")
        if submitted:
            governance_service.upsert_packaging_service(
                {
                    "packaging_service_id": service_id,
                    "name": name,
                    "material_type": material_type,
                    "unit": unit,
                    "base_price": base_price,
                    "price_per_unit": price_per_unit,
                    "minimum_charge": minimum_charge,
                    "applicable_product_categories": [item.strip() for item in categories.split(",") if item.strip()],
                    "status": status,
                }
            )
            st.success("Packaging service saved.")
            st.rerun()
    with manage_tab:
        if not services:
            st.info("No packaging services available yet.")
            return
        selected_id = st.selectbox("Manage Packaging Service", [item["packaging_service_id"] for item in services])
        selected = next(item for item in services if item["packaging_service_id"] == selected_id)
        with st.form("manage_packaging_service"):
            name = st.text_input("Name", value=selected.get("name", ""))
            material_type = st.selectbox("Material Type", ["BOX", "BAG", "WRAP", "CRATE", "CUSTOM"], index=["BOX", "BAG", "WRAP", "CRATE", "CUSTOM"].index(selected.get("material_type", "BOX")) if selected.get("material_type", "BOX") in {"BOX", "BAG", "WRAP", "CRATE", "CUSTOM"} else 0)
            unit = st.text_input("Unit", value=selected.get("unit", "piece"))
            base_price = st.number_input("Base Price", min_value=0.0, step=1.0, value=float(selected.get("base_price", 0) or 0))
            price_per_unit = st.number_input("Price Per Unit", min_value=0.0, step=1.0, value=float(selected.get("price_per_unit", 0) or 0))
            minimum_charge = st.number_input("Minimum Charge", min_value=0.0, step=1.0, value=float(selected.get("minimum_charge", 0) or 0))
            categories = st.text_input("Applicable Categories", value=", ".join(selected.get("applicable_product_categories", [])))
            status = st.selectbox("Status", ["ACTIVE", "INACTIVE", "ARCHIVED"], index=["ACTIVE", "INACTIVE", "ARCHIVED"].index(selected.get("status", "ACTIVE")) if selected.get("status", "ACTIVE") in {"ACTIVE", "INACTIVE", "ARCHIVED"} else 0)
            saved = st.form_submit_button("Update Packaging Service")
        if saved:
            governance_service.upsert_packaging_service(
                {
                    "packaging_service_id": selected_id,
                    "name": name,
                    "material_type": material_type,
                    "unit": unit,
                    "base_price": base_price,
                    "price_per_unit": price_per_unit,
                    "minimum_charge": minimum_charge,
                    "applicable_product_categories": [item.strip() for item in categories.split(",") if item.strip()],
                    "status": status,
                }
            )
            st.success("Packaging service updated.")
            st.rerun()
        if st.button("Archive Packaging Service", use_container_width=True):
            governance_service.archive_packaging_service(selected_id)
            st.warning("Packaging service archived.")
            st.rerun()
