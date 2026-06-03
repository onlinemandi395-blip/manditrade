from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.responsive_layout import render_section_intro
from components.ui_shell import render_showcase_strip


def render_login_page(app_context: dict) -> None:
    render_platform_shell(
        title="MandiTrade",
        subtitle="Digital Manpur for manufacturer networks, public marketplace trade, mandi-order sourcing, khata discipline, and role-aware operations after one Google sign-in.",
        badges=["Single Sign-In", "RBAC Routing", "Post-Login Marketplace"],
        role="Public Landing",
        metrics=[("Marketplace", "After sign-in"), ("Workspace Mode", "Role-aware")],
        kicker="Digital Manpur Public Landing",
        breadcrumbs=["Public", "Dashboard"],
        primary_actions=["Use sidebar sign-in"],
    )
    render_kpi_cards(
        [
            {"label": "Single Login", "value": "One entry for all users", "status": "SUCCESS"},
            {"label": "Role Routing", "value": "Automatic after sign-in", "status": "OPEN"},
            {"label": "Getting Started", "value": "Fast sign-in for every role", "status": "PENDING"},
        ]
    )
    render_showcase_strip(
        [
            ("Manufacturers", "Inventory + Mandi Orders + Jobs", "SUCCESS"),
            ("Mahajans", "Raw materials + supply orders", "OPEN"),
            ("Public Buyers", "Instant pay shopping", "SUCCESS"),
        ]
    )
    render_section_intro("Platform Overview", "Manufacturers, mahajans, workers, public buyers, and SuperUser all enter through one Google sign-in. The correct workspace loads automatically after authentication.")
    render_html(
        """
        <section class="mt-login-layout">
          <article class="mt-login-story">
            <div class="mt-login-story__grid"></div>
            <div class="mt-login-story__content">
              <p class="mt-kicker">Digital Manpur</p>
              <h3>Federated wholesale commerce with mandi lanes, khata clarity, and live operational control.</h3>
              <p>
                This workspace is built for Bharat market operations: product governance, mandi-order sourcing,
                inventory control, jobs, payments, and role-aware dashboards without forcing users through a generic storefront.
              </p>
              <div class="mt-login-story__nodes">
                <span class="mt-login-story__node">Mandi Orders</span>
                <span class="mt-login-story__node">Khata Visibility</span>
                <span class="mt-login-story__node">Manufacturer Control</span>
                <span class="mt-login-story__node">Supply Routing</span>
              </div>
            </div>
          </article>
          <article class="mt-login-card">
            <div class="mt-login-card__content">
              <p class="mt-kicker">After Sign-In</p>
              <h3>One public landing, multiple role-aware workspaces</h3>
              <p>
                Public buyers reach Marketplace after sign-in. Manufacturers unlock selling and mandi sourcing,
                mahajans handle supply execution, and role-scoped payments plus ledger workflows stay controlled after authentication.
              </p>
            </div>
          </article>
        </section>
        """
    )
    st.caption("Use the sign-in button in the sidebar to continue.")


def render_access_portal(app_context: dict) -> None:
    render_login_page(app_context)


def render_pending_user_dashboard(app_context: dict) -> None:
    current_user = app_context["current_user"]
    request = app_context["access_portal_service"].find_latest_request(current_user.email) if current_user else None
    render_platform_shell(
        title="Account Setup In Progress",
        subtitle="Your account is being prepared. Please check back soon or contact support if you need help.",
        badges=["Preparing Account"],
        role="Pending User",
        metrics=[("Status", "In Progress")],
        breadcrumbs=["Public", "Pending Account"],
    )
    render_kpi_cards(
        [
            {"label": "Account Status", "value": "In Progress", "status": "PENDING"},
            {"label": "Next Step", "value": "We will guide you shortly", "status": "WARNING"},
        ]
    )
    render_section_intro("Next Step", "If your access should already be active, contact support and we will help you complete setup.")
    if request:
        st.info("Your request has been received and is under review.")
    else:
        st.info("Your account is not fully ready yet.")
