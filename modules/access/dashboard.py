from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_action_grid, render_metric_grid
from components.ui_shell import render_action_card, render_metric_card, render_page_header


def _prime_access_context(*, requested_role: str, manufacturer_code: str = "", client_token: str = "") -> None:
    st.session_state["requested_role"] = requested_role
    st.session_state["manufacturer_context"] = manufacturer_code.strip().upper() or None
    st.session_state["client_onboarding_token"] = client_token.strip() or None


def render_access_portal(app_context: dict) -> None:
    render_page_header(
        "Welcome to MandiTrade",
        "Use one central login and signup hub, then land on your own RBAC dashboard after Google sign-in.",
        ["Google Sign-In Only", "RBAC Dashboard", "Central Access"],
    )
    render_metric_grid(
        [
            render_metric_card("Manufacturers", str(len(app_context["governance_service"].list_manufacturers())), "SUCCESS"),
            render_metric_card("Products", str(len(app_context["product_catalog_service"].list_products(include_pending=True))), "OPEN"),
            render_metric_card("Open Jobs", str(len(app_context["job_service"].list_open_jobs())), "PENDING"),
        ]
    )
    render_action_grid(
        [
            render_action_card("Manufacturer Login", "Use your Google account with your approved manufacturer code.", "Open login"),
            render_action_card("Client Login", "Use your invited Google email and manufacturer onboarding context.", "Open login"),
            render_action_card("Worker Signup", "Create a worker request first, then continue with Google sign-in.", "Open signup"),
        ]
    )
    render_section_intro("Central Access", "Login and signup both route through the same access control layer. After authentication, each user lands on their own dashboard.")

    login_tab, signup_tab = st.tabs(["Login", "Signup"])
    auth_url = app_context["oauth_callback_service"].build_authorization_url()

    with login_tab:
        role = st.radio("Login As", ["manufacturer", "client", "worker"], horizontal=True)
        manufacturer_code = ""
        client_token = ""
        if role in {"manufacturer", "client"}:
            manufacturer_code = st.text_input("Manufacturer Code", placeholder="MANU101", key="login_manufacturer_code")
        if role == "client":
            client_token = st.text_area("Client Invitation Token", key="login_client_token")
        if st.button("Prepare Google Login", use_container_width=True, key="prepare_google_login"):
            _prime_access_context(requested_role=role, manufacturer_code=manufacturer_code, client_token=client_token)
            st.success("Context prepared. Continue with Google below.")
        if auth_url and app_context["google_runtime_enabled"]:
            st.link_button("Continue with Google", auth_url, use_container_width=True)
        else:
            st.info("Google OAuth is not available yet in this runtime.")

    with signup_tab:
        role = st.radio("Signup As", ["manufacturer", "client", "worker"], horizontal=True, key="signup_role")
        with st.form("central_signup_form"):
            email = st.text_input("Email", placeholder="name@example.com")
            full_name = st.text_input("Full Name", placeholder="Ravi Kumar")
            manufacturer_code = st.text_input("Manufacturer Code", placeholder="MANU101")
            manufacturer_name = st.text_input("Manufacturer / Business Name", placeholder="Shree Agro Traders")
            city = st.text_input("City", placeholder="Pune")
            mobile = st.text_input("Mobile", placeholder="9876543210")
            area = st.text_input("Area", placeholder="Bhosari")
            skills = st.text_input("Skills", placeholder="Loading,Packaging")
            preferred_work_type = st.text_input("Preferred Work Types", placeholder="Daily Wage,Part-time")
            onboarding_secret = st.text_input("Manufacturer Onboarding Secret", type="password")
            invite_token = st.text_area("Client Invitation Token")
            note = st.text_area("Note", placeholder="Any extra info for admin review or worker onboarding.")
            submitted = st.form_submit_button("Submit Signup")
        if submitted and email and full_name:
            request = app_context["access_portal_service"].submit_signup_request(
                requested_role=role,
                email=email,
                full_name=full_name,
                manufacturer_code=manufacturer_code,
                manufacturer_name=manufacturer_name,
                city=city,
                mobile=mobile,
                area=area,
                skills=[item.strip() for item in skills.split(",")],
                preferred_work_type=[item.strip() for item in preferred_work_type.split(",")],
                onboarding_secret=onboarding_secret,
                invite_token=invite_token,
                business_name=manufacturer_name,
                note=note,
            )
            _prime_access_context(requested_role=role, manufacturer_code=manufacturer_code, client_token=invite_token)
            if request.get("status") == "READY_FOR_GOOGLE_SIGNIN":
                st.success(request.get("validation_message", "Signup request is ready. Continue with Google sign-in."))
            else:
                st.warning(request.get("validation_message", "Signup request saved. Wait for admin approval."))


def render_pending_user_dashboard(app_context: dict) -> None:
    current_user = app_context["current_user"]
    request = app_context["access_portal_service"].find_latest_request(current_user.email) if current_user else None
    render_page_header(
        "Access Pending",
        "Your Google account is authenticated, but your full workspace access is still being mapped into MandiTrade.",
        ["Pending Review", "RBAC Mapping"],
    )
    render_metric_grid(
        [
            render_metric_card("Current Role", current_user.role if current_user else "pending_user", "PENDING"),
            render_metric_card("Request Status", (request or {}).get("status", "NO_ACCESS_MAPPING"), "WARNING"),
        ]
    )
    render_section_intro("Next Step", "If you are a manufacturer or client, make sure your onboarding packet or invitation has been validated. Workers can complete signup from the central access page.")
    if request:
        st.write(request)
    else:
        st.info("No signup request was found for this email yet. Use the central signup flow or ask admin to onboard you.")
