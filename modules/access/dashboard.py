from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip


def render_login_page(app_context: dict) -> None:
    render_page_header(
        "MandiTrade",
        "Digital Manpur for manufacturer networks, public marketplace trade, RFQ sourcing, khata discipline, and role-aware operations after one Google sign-in.",
        ["Single Sign-In", "RBAC Routing", "Post-Login Marketplace"],
        role="Public Landing",
        metrics=[("Marketplace", "After sign-in"), ("Workspace Mode", "Role-aware")],
        kicker="Digital Manpur Public Landing",
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
    render_section_intro("Platform Overview", "Manufacturers, clients, workers, public buyers, and SuperUser all enter through one Google sign-in. The correct workspace loads automatically after authentication.")
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
              <p class="mt-kicker">After Sign-In</p>
              <h3>One public landing, multiple role-aware workspaces</h3>
              <p>
                Public buyers reach Marketplace after sign-in. Manufacturers unlock inventory, clients manage proposal orders,
                and RFQ plus khata workflows stay role-scoped after authentication.
              </p>
            </div>
          </article>
        </section>
        """
    )
    st.caption("Google sign-in is available in the top navigation. No role selector, marketplace shortcut, or separate access page is shown before login.")

    with st.expander("Need access help?", expanded=False):
        st.write("If your email is already onboarded, your dashboard will load automatically after login.")
        st.write("If you are a new public buyer entering from Marketplace, the app can create your marketplace profile after Google sign-in.")
        st.write("Manufacturer, client, or worker onboarding stays admin-managed in the backend.")


def render_access_portal(app_context: dict) -> None:
    render_login_page(app_context)


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
