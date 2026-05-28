from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_access_portal(app_context: dict) -> None:
    render_page_header(
        "Login to MandiTrade",
        "Sign in once with Google. MandiTrade will automatically load the right RBAC dashboard for your account.",
        ["Google Sign-In Only", "RBAC Auto Routing", "Secure Access"],
    )
    render_metric_grid(
        [
            render_metric_card("Single Login", "One entry for all users", "SUCCESS"),
            render_metric_card("Role Routing", "Automatic after sign-in", "OPEN"),
            render_metric_card("Workspace Access", "Based on onboarding and approvals", "PENDING"),
        ]
    )
    render_section_intro("Access", "Manufacturers, clients, workers, and platform admins all enter through one abstracted login page. Access is mapped in the background after authentication.")

    auth_url = app_context["oauth_callback_service"].build_authorization_url()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if auth_url and app_context["google_runtime_enabled"]:
            st.link_button("Continue with Google", auth_url, use_container_width=True)
        else:
            st.info("Google OAuth is not available yet in this runtime.")
        st.caption("No role selection, signup form, or onboarding token is shown on this page.")

    with st.expander("Need access help?", expanded=False):
        st.write("If your email is already onboarded, your dashboard will load automatically after login.")
        st.write("If access is still pending, MandiTrade will show a pending-access screen with next steps.")
        st.write("New manufacturer, client, or worker onboarding stays admin-managed in the backend.")


def render_pending_user_dashboard(app_context: dict) -> None:
    current_user = app_context["current_user"]
    request = app_context["access_portal_service"].find_latest_request(current_user.email) if current_user else None
    render_page_header(
        "Access Pending",
        "Your Google account is verified, but your MandiTrade workspace access is still being finalized.",
        ["Pending Review", "RBAC Mapping"],
    )
    render_metric_grid(
        [
            render_metric_card("Current Role", current_user.role if current_user else "pending_user", "PENDING"),
            render_metric_card("Request Status", (request or {}).get("status", "NO_ACCESS_MAPPING"), "WARNING"),
        ]
    )
    render_section_intro("Next Step", "Contact platform admin if this account should already have access. Once mapped, the correct dashboard will load automatically on next login.")
    if request:
        st.write(request)
    else:
        st.info("This email is authenticated but not yet linked to a MandiTrade role.")
