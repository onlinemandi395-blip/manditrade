from __future__ import annotations

import streamlit as st


def render_client_onboarding(app_context: dict) -> None:
    st.subheader("Client Onboarding")
    st.caption("Validate an invitation token and complete the client business profile.")

    client_service = app_context["client_service"]
    audit_service = app_context["audit_service"]
    current_user = app_context["current_user"]

    with st.form("client_onboarding_form"):
        manufacturer_code = st.text_input("Manufacturer Code", placeholder="MANU101")
        onboarding_token = st.text_area("Onboarding Token")
        business_name = st.text_input("Business Name", placeholder="Kumar Traders")
        owner_name = st.text_input("Owner Name", placeholder="Amit Kumar")
        city = st.text_input("City", placeholder="Pune")
        credit_limit = st.number_input("Credit Limit", min_value=0, value=50000, step=1000)
        submit = st.form_submit_button("Complete Onboarding")

    if submit and current_user and manufacturer_code and onboarding_token:
        invite = client_service.validate_onboarding(manufacturer_code.strip().upper(), onboarding_token.strip(), current_user.email)
        if not invite:
            st.error("Invitation validation failed.")
            return
        profile = {
            "client_id": invite["client_id"],
            "manufacturer_id": manufacturer_code.strip().upper(),
            "business_name": business_name.strip() or invite.get("business_name", ""),
            "owner_name": owner_name.strip(),
            "email": current_user.email,
            "city": city.strip(),
            "credit_limit": int(credit_limit),
            "status": "ACTIVE",
        }
        client_service.complete_profile(manufacturer_code.strip().upper(), profile)
        audit_service.log_event(
            "client_onboarding_completed",
            actor=current_user.email,
            details={"client_id": profile["client_id"], "manufacturer_id": profile["manufacturer_id"]},
        )
        st.success("Client profile activated.")
