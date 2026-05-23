from __future__ import annotations

import streamlit as st


def render_manufacturer_onboarding(app_context: dict) -> None:
    st.subheader("Manufacturer Onboarding")
    st.caption("Creates the manufacturer workspace with shared and private zones, then registers it for admin approval.")

    drive_service = app_context["drive_service"]
    governance_service = app_context["governance_service"]
    audit_service = app_context["audit_service"]
    current_user = app_context["current_user"]

    with st.form("manufacturer_onboarding_form"):
        manufacturer_code = st.text_input("Manufacturer Code", placeholder="MANU101")
        manufacturer_name = st.text_input("Manufacturer Name", placeholder="Shree Agro Traders")
        owner_email = st.text_input("Owner Email", placeholder="owner@example.com")
        city = st.text_input("Operating City", placeholder="Jaipur")
        submit = st.form_submit_button("Initialize Manufacturer Workspace")

    if submit and manufacturer_code and manufacturer_name:
        normalized_code = manufacturer_code.strip().upper()
        paths = drive_service.initialize_manufacturer_workspace(
            manufacturer_code=normalized_code,
            manufacturer_name=manufacturer_name.strip(),
            owner_email=owner_email.strip(),
            city=city.strip(),
            status="pending_approval",
        )
        governance_service.register_manufacturer(
            {
                "manufacturer_code": normalized_code,
                "manufacturer_name": manufacturer_name.strip(),
                "owner_email": owner_email.strip(),
                "city": city.strip(),
                "status": "pending_approval",
                "subscription_plan": "basic",
            }
        )
        actor = current_user.email if current_user else owner_email.strip() or "system"
        audit_service.log_event(
            "manufacturer_onboarding_initialized",
            actor=actor,
            details={"manufacturer_code": normalized_code, "manufacturer_name": manufacturer_name.strip()},
        )
        st.success(f"Workspace initialized for {manufacturer_name}.")
        st.code(
            f"Shared Zone: {paths.shared_zone}\nPrivate Zone: {paths.private_zone}\nOwner Email: {owner_email or 'not recorded yet'}\nStatus: pending_approval",
            language="text",
        )

    st.markdown("### Registered Manufacturers")
    st.dataframe(governance_service.list_manufacturers(), use_container_width=True)
