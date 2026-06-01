from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_mahajans_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    procurement_service = app_context["procurement_transaction_service"]
    mahajans = governance_service.list_mahajans()
    supply_orders = procurement_service.list_supply_orders()
    pending_invites = [item for item in mahajans if item.get("status") == "INVITED"]
    active = [item for item in mahajans if item.get("status") == "ACTIVE"]

    render_page_header(
        "Mahajans",
        "Manage admin-controlled raw-material suppliers and track the upstream supply channel without exposing manufacturers to direct supplier access.",
        ["Platform Admin", "Supply Control"],
    )
    render_metric_grid(
        [
            render_metric_card("Total Mahajans", str(len(mahajans)), "OPEN"),
            render_metric_card("Active Mahajans", str(len(active)), "SUCCESS"),
            render_metric_card("Pending Invites", str(len(pending_invites)), "PENDING"),
            render_metric_card("Open Supply Orders", str(len([item for item in supply_orders if item.get("status") not in {'CLOSED', 'CANCELLED'}])), "WARNING"),
        ]
    )
    overview_tab, registry_tab, invite_tab, manage_tab = st.tabs(["Overview", "Registry", "Invite/Create", "Manage"])
    with overview_tab:
        render_section_intro("Supply Channel", "Mahajan is the admin-managed upstream supplier role. Manufacturers do not deal with mahajans directly.")
        st.dataframe(mahajans, use_container_width=True)
    with registry_tab:
        st.dataframe(supply_orders, use_container_width=True)
    with invite_tab:
        with st.form("create_mahajan"):
            mahajan_id = st.text_input("Mahajan ID", value=f"MAH{len(mahajans) + 1:03d}")
            business_name = st.text_input("Business Name")
            owner_name = st.text_input("Owner Name")
            email = st.text_input("Email")
            mobile = st.text_input("Mobile")
            city = st.text_input("City")
            status = st.selectbox("Status", ["INVITED", "ACTIVE", "INACTIVE"], index=0)
            submitted = st.form_submit_button("Save Mahajan")
        if submitted and mahajan_id.strip() and email.strip():
            governance_service.upsert_mahajan(
                {
                    "mahajan_id": mahajan_id,
                    "business_name": business_name,
                    "owner_name": owner_name,
                    "email": email,
                    "mobile": mobile,
                    "city": city,
                    "status": status,
                }
            )
            st.success("Mahajan saved.")
            st.rerun()
    with manage_tab:
        if not mahajans:
            st.info("No mahajans registered yet.")
        else:
            selected_id = st.selectbox("Manage Mahajan", [item["mahajan_id"] for item in mahajans])
            selected = next(item for item in mahajans if item["mahajan_id"] == selected_id)
            with st.form("manage_mahajan"):
                business_name = st.text_input("Business Name", value=selected.get("business_name", ""))
                owner_name = st.text_input("Owner Name", value=selected.get("owner_name", ""))
                email = st.text_input("Email", value=selected.get("email", ""))
                mobile = st.text_input("Mobile", value=selected.get("mobile", ""))
                city = st.text_input("City", value=selected.get("city", ""))
                status = st.selectbox("Status", ["INVITED", "ACTIVE", "INACTIVE"], index=["INVITED", "ACTIVE", "INACTIVE"].index(selected.get("status", "INVITED")) if selected.get("status", "INVITED") in {"INVITED", "ACTIVE", "INACTIVE"} else 0)
                saved = st.form_submit_button("Update Mahajan")
            if saved:
                governance_service.upsert_mahajan(
                    {
                        "mahajan_id": selected_id,
                        "business_name": business_name,
                        "owner_name": owner_name,
                        "email": email,
                        "mobile": mobile,
                        "city": city,
                        "status": status,
                    }
                )
                st.success("Mahajan updated.")
                st.rerun()
