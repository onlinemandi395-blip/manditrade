from __future__ import annotations

import streamlit as st

from modules.admin.dashboard import render_admin_dashboard
from modules.agreements.dashboard import render_agreements_dashboard
from modules.analytics.dashboard import render_analytics_dashboard
from modules.client.dashboard import render_client_dashboard
from modules.client.onboarding import render_client_onboarding
from modules.inventory.management import render_inventory_management
from modules.manufacturer.dashboard import render_manufacturer_dashboard
from modules.notifications.dashboard import render_notifications_dashboard
from modules.onboarding.manufacturer_onboarding import render_manufacturer_onboarding
from modules.orders.dispatch import render_dispatch_management
from modules.pricing.dashboard import render_pricing_dashboard
from modules.procurement.dashboard import render_procurement_dashboard
from modules.system.health_dashboard import render_health_dashboard


def render_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    if not user:
        st.subheader("Platform Overview")
        st.write("Sign in to access role-based dashboards and manufacturer workspaces.")
        st.write(
            {
                "environment": app_context["system_config"]["app"]["environment"],
                "drive_mode": app_context["drive_service"].describe_runtime_mode(),
                "gmail_mode": "Live" if app_context["system_config"]["notifications"]["use_gmail_api"] else "Mocked",
                "security_model": "public-key verified runtime access",
            }
        )
        return
    if user.role == "admin":
        render_admin_dashboard(app_context)
    elif user.role == "manufacturer":
        render_manufacturer_dashboard(app_context)
    else:
        render_client_dashboard(app_context)


def render_route(section: str, app_context: dict) -> None:
    if section == "Dashboard":
        render_dashboard(app_context)
    elif section == "Onboarding":
        render_manufacturer_onboarding(app_context)
    elif section == "Inventory":
        render_inventory_management(app_context)
    elif section == "Pricing":
        render_pricing_dashboard(app_context)
    elif section == "Procurement":
        render_procurement_dashboard(app_context)
    elif section == "Agreements":
        render_agreements_dashboard(app_context)
    elif section == "Notifications":
        render_notifications_dashboard(app_context)
    elif section == "Dispatch":
        render_dispatch_management(app_context)
    elif section == "Analytics":
        render_analytics_dashboard(app_context)
    elif section == "System Health":
        render_health_dashboard(app_context)
    elif section == "Client Onboarding":
        render_client_onboarding(app_context)
    elif section == "Client":
        render_client_dashboard(app_context)
