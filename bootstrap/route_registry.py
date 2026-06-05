from __future__ import annotations

import streamlit as st

from constants.roles import ROLE_MANUFACTURER, ROLE_MAHAJAN, ROLE_PENDING_USER, ROLE_PLATFORM_ADMIN, ROLE_PUBLIC_BUYER, ROLE_WORKER
from modules.access.dashboard import render_login_page, render_pending_user_dashboard
from modules.actions.dashboard import render_actions_dashboard
from modules.account_status.dashboard import render_account_status_dashboard
from modules.analytics.dashboard import render_analytics_dashboard
from modules.admin.commission_summary import render_commission_summary_dashboard
from modules.admin.finance_operations import render_finance_operations_dashboard
from modules.finance.commission_dashboard import render_commission_dashboard
from modules.admin.dashboard import render_admin_dashboard
from modules.admin.operations_dashboard import render_operations_dashboard
from modules.admin.mahajans import render_mahajans_dashboard
from modules.admin.packaging_services import render_packaging_services_dashboard
from modules.admin.courier_services import render_courier_services_dashboard
from modules.admin.inventory_summary import render_inventory_summary_dashboard
from modules.admin.manufacturers import render_manufacturers_dashboard
from modules.admin.procurement_sources import render_procurement_sources_dashboard
from modules.admin.workers import render_workers_admin_dashboard
from modules.mahajan.dashboard import render_mahajan_dashboard
from modules.admin.product_approvals import render_product_approvals_dashboard
from modules.inventory.management import render_inventory_management
from modules.jobs.dashboard import render_jobs_dashboard
from modules.ledger.dashboard import render_ledger_dashboard
from modules.manufacturer.dashboard import render_manufacturer_dashboard
from modules.marketplace.dashboard import render_marketplace_dashboard
from modules.notifications.dashboard import render_notifications_dashboard
from modules.onboarding.manufacturer_onboarding import render_manufacturer_onboarding
from modules.orders.dashboard import render_orders_dashboard
from modules.orders.dispatch import render_dispatch_management
from modules.orders.hub import render_my_orders_hub, render_orders_hub
from modules.payments.dashboard import render_payments_dashboard
from modules.profile.dashboard import render_my_profile_dashboard
from modules.procurement.dashboard import render_procurement_dashboard
from modules.products.dashboard import render_products_dashboard
from modules.public_buyer.dashboard import render_public_buyer_dashboard
from modules.public_orders.dashboard import render_public_orders_dashboard
from modules.raw_materials.dashboard import render_raw_materials_dashboard
from modules.suta_mandi.dashboard import render_suta_mandi_dashboard
from modules.system.admin_drive_db import render_admin_drive_db_dashboard
from modules.system.health_dashboard import render_health_dashboard
from modules.logistics.dashboard import render_logistics_dashboard
from modules.shipments.dashboard import render_shipments_dashboard
from modules.workers.dashboard import render_workers_dashboard
from modules.warehouses.dashboard import render_warehouses_dashboard
from services.navigation_service import NAV_ALIAS_MAP, normalize_navigation_route


ROUTE_GROUPS = {
    "public": {"dashboard"},
    "shared_authenticated": {"dashboard", "my_profile", "notifications", "my_actions"},
    ROLE_PLATFORM_ADMIN: {
        "dashboard",
        "my_profile",
        "notifications",
        "my_actions",
        "manufacturers",
        "mahajans",
        "workers",
        "products",
        "procurement_sources",
        "product_approvals",
        "orders",
        "inventory",
        "payments",
        "ledger",
        "platform_commission",
        "warehouses",
        "shipments",
        "system_health",
        "analytics",
        "admin_drive_db",
    },
    ROLE_MAHAJAN: {"dashboard", "my_profile", "notifications", "my_actions", "warehouses", "raw_materials", "shipments", "my_orders", "payments", "ledger", "jobs", "orders"},
    ROLE_MANUFACTURER: {"dashboard", "my_profile", "notifications", "my_actions", "products", "warehouses", "inventory", "shipments", "marketplace", "mandiplace", "my_orders", "orders", "raw_materials", "suta_mandi", "payments", "ledger", "jobs"},
    ROLE_PUBLIC_BUYER: {"dashboard", "my_profile", "notifications", "my_actions", "marketplace", "my_orders", "jobs"},
    ROLE_WORKER: {"dashboard", "my_profile", "notifications", "my_actions", "jobs"},
}


def can_access_route(user, section: str, app_context: dict) -> bool:
    normalized_section = normalize_navigation_route(section)
    if not user:
        return normalized_section in ROUTE_GROUPS["public"]
    session_user = app_context.get("session_user") or user
    security_service = app_context["security_service"]
    role = (user.role or "").strip().lower()
    if normalized_section in ROUTE_GROUPS["shared_authenticated"]:
        return True
    if security_service.is_admin_identity(session_user) and role == ROLE_PLATFORM_ADMIN:
        return normalized_section in ROUTE_GROUPS[ROLE_PLATFORM_ADMIN]
    if role == "admin_as_manufacturer":
        return normalized_section in ROUTE_GROUPS[ROLE_MANUFACTURER]
    if role in ROUTE_GROUPS:
        return normalized_section in ROUTE_GROUPS[role]
    if role == ROLE_PENDING_USER:
        return normalized_section == "dashboard"
    return False


def _render_access_denied(app_context: dict) -> None:
    render_account_status_dashboard(
        app_context,
        title="Access Denied",
        subtitle="This page is not available for your current role. Your workspace is still active, but this route stays restricted by platform policy.",
    )


def render_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    if not user:
        render_login_page(app_context)
        return
    if app_context["security_service"].is_admin_identity(app_context.get("session_user") or user) and user.role == ROLE_PLATFORM_ADMIN:
        render_admin_dashboard(app_context)
    elif user.role == ROLE_MAHAJAN:
        render_mahajan_dashboard(app_context)
    elif user.role in {ROLE_MANUFACTURER, "admin_as_manufacturer"}:
        render_manufacturer_dashboard(app_context)
    elif user.role == ROLE_WORKER:
        render_workers_dashboard(app_context)
    elif user.role == ROLE_PUBLIC_BUYER:
        render_public_buyer_dashboard(app_context)
    elif user.role == ROLE_PENDING_USER:
        render_pending_user_dashboard(app_context)
    else:
        render_account_status_dashboard(app_context, title="Access Pending", subtitle="This workspace is not mapped to an active commerce role.")


def render_route(section: str, app_context: dict) -> None:
    section = normalize_navigation_route(section)
    user = app_context.get("current_user")
    session_user = app_context.get("session_user") or user
    is_admin_identity = app_context["security_service"].is_admin_identity(session_user)
    supervisor_mode = bool(is_admin_identity and getattr(user, "role", "") == ROLE_PLATFORM_ADMIN)
    if not user:
        if section == "marketplace":
            st.session_state["requested_role"] = ROLE_PUBLIC_BUYER
        render_login_page(app_context)
        return
    if not can_access_route(user, section, app_context):
        _render_access_denied(app_context)
        return
    if section == "dashboard":
        render_dashboard(app_context)
    elif section == "my_actions":
        render_actions_dashboard(app_context)
    elif section == "notifications":
        render_notifications_dashboard(app_context)
    elif section == "my_profile":
        render_my_profile_dashboard(app_context)
    elif section == "products":
        render_products_dashboard(app_context)
    elif section == "procurement_sources":
        render_procurement_sources_dashboard(app_context)
    elif section == "mandiplace":
        render_procurement_dashboard(app_context)
    elif section == "suta_mandi":
        render_suta_mandi_dashboard(app_context)
    elif section == "marketplace":
        render_marketplace_dashboard(app_context)
    elif section == "orders":
        current_user = app_context.get("current_user")
        if current_user and current_user.role == ROLE_PLATFORM_ADMIN:
            render_orders_hub(app_context)
        else:
            render_my_orders_hub(app_context)
    elif section == "my_orders":
        render_my_orders_hub(app_context)
    elif section == "inventory":
        render_inventory_management(app_context)
    elif section == "warehouses":
        render_warehouses_dashboard(app_context)
    elif section == "shipments":
        render_shipments_dashboard(app_context)
    elif section == "ledger":
        if supervisor_mode:
            render_admin_dashboard(app_context, section="Ledger")
        else:
            render_ledger_dashboard(app_context)
    elif section in {"payments", "platform_commission"}:
        if section == "platform_commission" and supervisor_mode:
            render_commission_summary_dashboard(app_context)
        elif section == "platform_commission":
            render_commission_dashboard(app_context)
        elif supervisor_mode:
            render_admin_dashboard(app_context, section="Payments")
        else:
            render_payments_dashboard(app_context)
    elif section == "finance_operations":
        if "settlement_service" in app_context and "invoice_service" in app_context and "dispute_service" in app_context:
            render_finance_operations_dashboard(app_context)
        elif supervisor_mode:
            render_admin_dashboard(app_context, section="Finance Operations")
        else:
            _render_access_denied(app_context)
    elif section == "dispatch":
        render_dispatch_management(app_context)
    elif section == "mahajans":
        render_mahajans_dashboard(app_context)
    elif section == "workers":
        render_workers_admin_dashboard(app_context)
    elif section == "raw_materials":
        render_raw_materials_dashboard(app_context)
    elif section == "operations_center":
        render_operations_dashboard(app_context)
    elif section == "packaging_services":
        render_packaging_services_dashboard(app_context)
    elif section == "courier_services":
        render_courier_services_dashboard(app_context)
    elif section == "logistics":
        render_logistics_dashboard(app_context)
    elif section == "jobs":
        render_jobs_dashboard(app_context)
    elif section == "analytics":
        render_analytics_dashboard(app_context)
    elif section == "product_approvals":
        render_product_approvals_dashboard(app_context)
    elif section == "manufacturers":
        render_manufacturers_dashboard(app_context)
    elif section == "inventory_summary":
        render_inventory_summary_dashboard(app_context)
    elif section == "onboarding":
        render_manufacturer_onboarding(app_context)
    elif section == "system_health":
        render_health_dashboard(app_context)
    elif section == "admin_drive_db":
        render_admin_drive_db_dashboard(app_context)
    else:
        _render_access_denied(app_context)
