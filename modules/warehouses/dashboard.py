from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.entity_form import render_entity_form
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from utils.page_ui import render_empty_state


def _warehouse_scope(app_context: dict, user) -> tuple[str | None, str | None]:
    if not user:
        return None, None
    if user.role == "platform_admin":
        return None, None
    if user.role in {"manufacturer", "admin_as_manufacturer"}:
        return "manufacturer", user.manufacturer_code or ""
    if user.role == "mahajan":
        mahajan = app_context["governance_service"].get_mahajan_by_email(user.email)
        return "mahajan", (mahajan or {}).get("mahajan_id", "")
    return None, None


def render_warehouses_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    owner_role, owner_id = _warehouse_scope(app_context, user)
    warehouses = governance_service.list_warehouses(owner_role=owner_role, owner_id=owner_id)
    all_manufacturers = governance_service.list_manufacturers()
    all_mahajans = governance_service.list_mahajans()

    render_platform_shell(
        title="Warehouses",
        subtitle="Manage storage locations for manufacturers and mahajans so stock and shipments can be routed through real warehouse records.",
        badges=["Warehouse Network", user.role.replace("_", " ").title() if user else "Role"],
        role=user.role.replace("_", " ").title() if user else "Warehouse View",
        metrics=[("Warehouses", str(len(warehouses))), ("Default Sites", str(len([item for item in warehouses if item.get("is_default")])) )],
        breadcrumbs=["Workspace", "Logistics", "Warehouses"],
        primary_actions=["Create Warehouse"],
    )
    render_kpi_cards(
        [
            {"label": "Active Warehouses", "value": str(len([item for item in warehouses if item.get("status") == "ACTIVE"])), "status": "SUCCESS"},
            {"label": "Default Sites", "value": str(len([item for item in warehouses if item.get("is_default")])), "status": "OPEN"},
            {"label": "Paused", "value": str(len([item for item in warehouses if item.get("status") != "ACTIVE"])), "status": "WARNING"},
        ]
    )

    overview_tab, create_tab, manage_tab = st.tabs(["Overview", "Create Warehouse", "Manage"])
    with overview_tab:
        render_section_intro("Warehouse Directory", "Warehouse records now anchor inventory pools and shipment source locations.")
        if warehouses:
            render_data_grid(
                page_key="warehouse_directory",
                rows=warehouses,
                search_fields=["warehouse_id", "warehouse_name", "owner_id", "city", "state", "pincode"],
                status_field="status",
                date_field="updated_at",
                search_placeholder="Search warehouse, owner, or city",
            )
        else:
            render_empty_state("No warehouses created yet.")

    with create_tab:
        with render_entity_form("warehouse_create_form", title="Create Warehouse"):
            warehouse_id = st.text_input("Warehouse ID", value=f"WH{len(warehouses) + 1:03d}")
            selected_owner_role = owner_role or st.selectbox("Owner Role", ["manufacturer", "mahajan"])
            selected_owner_id = owner_id or ""
            if not owner_id:
                options = (
                    [item.get("manufacturer_code", "") for item in all_manufacturers]
                    if selected_owner_role == "manufacturer"
                    else [item.get("mahajan_id", "") for item in all_mahajans]
                )
                selected_owner_id = st.selectbox("Owner ID", options) if options else ""
            warehouse_name = st.text_input("Warehouse Name")
            contact_person = st.text_input("Contact Person")
            phone = st.text_input("Phone")
            address = st.text_area("Address")
            city_col, state_col, pin_col = st.columns(3)
            city = city_col.text_input("City")
            state = state_col.text_input("State")
            pincode = pin_col.text_input("Pincode")
            lat_col, lon_col, cap_col = st.columns(3)
            latitude = lat_col.text_input("Latitude")
            longitude = lon_col.text_input("Longitude")
            capacity = cap_col.number_input("Capacity", min_value=0.0, step=10.0)
            is_default = st.checkbox("Default Warehouse", value=not bool(warehouses))
            submitted = st.form_submit_button("Save Warehouse")
        if submitted and warehouse_id.strip() and warehouse_name.strip() and selected_owner_id:
            governance_service.upsert_warehouse(
                {
                    "warehouse_id": warehouse_id,
                    "owner_role": selected_owner_role,
                    "owner_id": selected_owner_id,
                    "warehouse_name": warehouse_name,
                    "contact_person": contact_person,
                    "phone": phone,
                    "address": address,
                    "city": city,
                    "state": state,
                    "pincode": pincode,
                    "latitude": latitude,
                    "longitude": longitude,
                    "capacity": float(capacity or 0),
                    "status": "ACTIVE",
                    "is_default": is_default,
                }
            )
            st.success("Warehouse saved.")
            st.rerun()

    with manage_tab:
        if not warehouses:
            st.info("No warehouses available to manage yet.")
        else:
            selected_id = st.selectbox("Select Warehouse", [item["warehouse_id"] for item in warehouses])
            selected = next(item for item in warehouses if item["warehouse_id"] == selected_id)
            with render_entity_form("warehouse_manage_form", title="Update Warehouse"):
                warehouse_name = st.text_input("Warehouse Name", value=selected.get("warehouse_name", ""))
                contact_person = st.text_input("Contact Person", value=selected.get("contact_person", ""))
                phone = st.text_input("Phone", value=selected.get("phone", ""))
                address = st.text_area("Address", value=selected.get("address", ""))
                city_col, state_col, pin_col = st.columns(3)
                city = city_col.text_input("City", value=selected.get("city", ""))
                state = state_col.text_input("State", value=selected.get("state", ""))
                pincode = pin_col.text_input("Pincode", value=selected.get("pincode", ""))
                lat_col, lon_col, cap_col = st.columns(3)
                latitude = lat_col.text_input("Latitude", value=selected.get("latitude", ""))
                longitude = lon_col.text_input("Longitude", value=selected.get("longitude", ""))
                capacity = cap_col.number_input("Capacity", min_value=0.0, step=10.0, value=float(selected.get("capacity", 0) or 0))
                status = st.selectbox("Status", ["ACTIVE", "INACTIVE", "ARCHIVED"], index=["ACTIVE", "INACTIVE", "ARCHIVED"].index(selected.get("status", "ACTIVE")) if selected.get("status", "ACTIVE") in {"ACTIVE", "INACTIVE", "ARCHIVED"} else 0)
                is_default = st.checkbox("Default Warehouse", value=bool(selected.get("is_default")))
                submitted = st.form_submit_button("Update Warehouse")
            if submitted:
                governance_service.upsert_warehouse(
                    {
                        **selected,
                        "warehouse_name": warehouse_name,
                        "contact_person": contact_person,
                        "phone": phone,
                        "address": address,
                        "city": city,
                        "state": state,
                        "pincode": pincode,
                        "latitude": latitude,
                        "longitude": longitude,
                        "capacity": float(capacity or 0),
                        "status": status,
                        "is_default": is_default,
                    }
                )
                st.success("Warehouse updated.")
                st.rerun()
