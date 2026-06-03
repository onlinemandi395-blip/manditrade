from __future__ import annotations

import streamlit as st

from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from utils.page_ui import render_empty_state


def render_courier_services_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    services = governance_service.list_courier_services()
    active = [item for item in services if item.get("status") == "ACTIVE"]
    render_page_header(
        "Courier Services",
        "Admin maintains courier and logistics providers for routed procurement workflows.",
        ["Platform Admin", "Logistics Catalog"],
    )
    render_metric_grid(
        [
            render_metric_card("Total Providers", str(len(services)), "OPEN"),
            render_metric_card("Active Providers", str(len(active)), "SUCCESS"),
            render_metric_card("Archived", str(len([item for item in services if item.get('status') == 'ARCHIVED'])), "WARNING"),
        ]
    )
    overview_tab, create_tab, manage_tab = st.tabs(["Overview", "Create", "Manage"])
    with overview_tab:
        render_section_intro("Courier Rate Cards", "Courier providers stay admin-managed so ordering manufacturers never bypass routed logistics control.")
        if services:
            filtered = render_filter_bar(
                page_key="courier_services",
                rows=services,
                search_fields=["courier_service_id", "provider_name", "service_type", "contact_name"],
                status_field="status",
                date_field="updated_at",
            )
            st.dataframe(filtered, use_container_width=True)
        else:
            render_empty_state("No courier services added yet.")
    with create_tab:
        with st.form("create_courier_service"):
            service_id = st.text_input("Courier Service ID", value=f"COURIER-{len(services)+1:04d}")
            provider_name = st.text_input("Provider Name")
            service_type = st.selectbox("Service Type", ["LOCAL", "INTERCITY", "BULK", "SAME_DAY", "CUSTOM"])
            base_price = st.number_input("Base Price", min_value=0.0, step=1.0)
            price_per_km = st.number_input("Price Per KM", min_value=0.0, step=1.0)
            price_per_kg = st.number_input("Price Per KG", min_value=0.0, step=1.0)
            minimum_charge = st.number_input("Minimum Charge", min_value=0.0, step=1.0)
            supported_locations = st.text_input("Supported Locations", placeholder="Delhi, Jaipur, Surat")
            contact_name = st.text_input("Contact Name")
            contact_mobile = st.text_input("Contact Mobile")
            status = st.selectbox("Status", ["ACTIVE", "INACTIVE", "ARCHIVED"])
            submitted = st.form_submit_button("Save Courier Service")
        if submitted:
            governance_service.upsert_courier_service(
                {
                    "courier_service_id": service_id,
                    "provider_name": provider_name,
                    "service_type": service_type,
                    "base_price": base_price,
                    "price_per_km": price_per_km,
                    "price_per_kg": price_per_kg,
                    "minimum_charge": minimum_charge,
                    "supported_locations": [item.strip() for item in supported_locations.split(",") if item.strip()],
                    "contact_name": contact_name,
                    "contact_mobile": contact_mobile,
                    "status": status,
                }
            )
            st.success("Courier service saved.")
            st.rerun()
    with manage_tab:
        if not services:
            st.info("No courier services available yet.")
            return
        selected_id = st.selectbox("Manage Courier Service", [item["courier_service_id"] for item in services])
        selected = next(item for item in services if item["courier_service_id"] == selected_id)
        with st.form("manage_courier_service"):
            provider_name = st.text_input("Provider Name", value=selected.get("provider_name", ""))
            service_type = st.selectbox("Service Type", ["LOCAL", "INTERCITY", "BULK", "SAME_DAY", "CUSTOM"], index=["LOCAL", "INTERCITY", "BULK", "SAME_DAY", "CUSTOM"].index(selected.get("service_type", "LOCAL")) if selected.get("service_type", "LOCAL") in {"LOCAL", "INTERCITY", "BULK", "SAME_DAY", "CUSTOM"} else 0)
            base_price = st.number_input("Base Price", min_value=0.0, step=1.0, value=float(selected.get("base_price", 0) or 0))
            price_per_km = st.number_input("Price Per KM", min_value=0.0, step=1.0, value=float(selected.get("price_per_km", 0) or 0))
            price_per_kg = st.number_input("Price Per KG", min_value=0.0, step=1.0, value=float(selected.get("price_per_kg", 0) or 0))
            minimum_charge = st.number_input("Minimum Charge", min_value=0.0, step=1.0, value=float(selected.get("minimum_charge", 0) or 0))
            supported_locations = st.text_input("Supported Locations", value=", ".join(selected.get("supported_locations", [])))
            contact_name = st.text_input("Contact Name", value=selected.get("contact_name", ""))
            contact_mobile = st.text_input("Contact Mobile", value=selected.get("contact_mobile", ""))
            status = st.selectbox("Status", ["ACTIVE", "INACTIVE", "ARCHIVED"], index=["ACTIVE", "INACTIVE", "ARCHIVED"].index(selected.get("status", "ACTIVE")) if selected.get("status", "ACTIVE") in {"ACTIVE", "INACTIVE", "ARCHIVED"} else 0)
            saved = st.form_submit_button("Update Courier Service")
        if saved:
            governance_service.upsert_courier_service(
                {
                    "courier_service_id": selected_id,
                    "provider_name": provider_name,
                    "service_type": service_type,
                    "base_price": base_price,
                    "price_per_km": price_per_km,
                    "price_per_kg": price_per_kg,
                    "minimum_charge": minimum_charge,
                    "supported_locations": [item.strip() for item in supported_locations.split(",") if item.strip()],
                    "contact_name": contact_name,
                    "contact_mobile": contact_mobile,
                    "status": status,
                }
            )
            st.success("Courier service updated.")
            st.rerun()
        if st.button("Archive Courier Service", use_container_width=True):
            governance_service.archive_courier_service(selected_id)
            st.warning("Courier service archived.")
            st.rerun()
