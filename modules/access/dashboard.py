from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_new_tab_link_button, render_page_header, render_showcase_strip


def render_access_portal(app_context: dict) -> None:
    render_page_header(
        "Login to MandiTrade",
        "Sign in once with Google. MandiTrade will automatically load the right RBAC dashboard for your account.",
        ["Google Sign-In Only", "RBAC Auto Routing", "Secure Access"],
        role="Universal Entry",
        metrics=[("Workspace Mode", "Role-aware"), ("Delivery Surface", "Google-only access")],
        kicker="Digital Manpur Access Layer",
    )
    render_metric_grid(
        [
            render_metric_card("Single Login", "One entry for all users", "SUCCESS"),
            render_metric_card("Role Routing", "Automatic after sign-in", "OPEN"),
            render_metric_card("Workspace Access", "Based on onboarding and approvals", "PENDING"),
        ]
    )
    render_showcase_strip(
        [
            ("Manufacturers", "Inventory + RFQ + Jobs", "SUCCESS"),
            ("Clients", "Orders + Khata visibility", "OPEN"),
            ("Public Buyers", "Instant pay shopping", "SUCCESS"),
        ]
    )
    render_section_intro("Access", "Manufacturers, clients, workers, and platform admins all enter through one abstracted login page. Access is mapped in the background after authentication.")
    render_html(
        """
        <section class="mt-login-layout">
          <article class="mt-login-story">
            <div class="mt-login-story__grid"></div>
            <div class="mt-login-story__content">
              <p class="mt-kicker">Digital Manpur</p>
              <h3>Federated wholesale commerce with mandi lanes, khata clarity, and live operational control.</h3>
              <p>
                This workspace is built for Bharat market operations: product governance, RFQ sourcing,
                inventory control, jobs, payments, and role-aware dashboards without forcing users through a generic storefront.
              </p>
              <div class="mt-login-story__nodes">
                <span class="mt-login-story__node">Mandi Network</span>
                <span class="mt-login-story__node">Khata Visibility</span>
                <span class="mt-login-story__node">Manufacturer Control</span>
                <span class="mt-login-story__node">Client Routing</span>
              </div>
            </div>
          </article>
          <article class="mt-login-card">
            <div class="mt-login-card__content">
              <p class="mt-kicker">Google Sign-In</p>
              <h3>One secure login for every role</h3>
              <p>
                Continue with Google to open the correct workspace automatically. No role picker
                or token entry is shown here.
              </p>
            </div>
          </article>
        </section>
        """
    )

    login_blocked_for_cloud_fallback = (
        app_context["system_config"]["app"].get("runtime_environment") == "staging_cloud"
        and app_context.get("oauth_config_fallback_active", False)
    )
    auth_url = None if login_blocked_for_cloud_fallback else app_context["oauth_callback_service"].build_authorization_url(flow_type=app_context["oauth_callback_service"].LOGIN)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if login_blocked_for_cloud_fallback:
            st.error("Cloud runtime is using local OAuth fallback. Configure Streamlit secrets.")
        elif auth_url and app_context["google_runtime_enabled"]:
            render_html(render_new_tab_link_button("Continue with Google", auth_url))
        else:
            st.info("Google OAuth is not available yet in this runtime.")
        st.caption("No role selection, signup form, or onboarding token is shown on this page.")
        if app_context["system_config"]["app"].get("safe_mode", False) or app_context["system_config"]["app"].get("staging_mode", False):
            with st.expander("OAuth Debug", expanded=False):
                st.json(app_context["oauth_callback_service"].oauth_debug_snapshot())

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
