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
from modules.payments.dashboard import render_payments_dashboard
from modules.profile.dashboard import render_my_profile_dashboard
from modules.procurement.dashboard import render_procurement_dashboard
from modules.products.dashboard import render_products_dashboard
from modules.public_buyer.dashboard import render_public_buyer_dashboard
from modules.public_orders.dashboard import render_public_orders_dashboard
from modules.raw_materials.dashboard import render_raw_materials_dashboard
from modules.suta_mandi.dashboard import render_suta_mandi_dashboard
from modules.system.health_dashboard import render_health_dashboard
from modules.logistics.dashboard import render_logistics_dashboard
from modules.shipments.dashboard import render_shipments_dashboard
from modules.workers.dashboard import render_workers_dashboard
from modules.warehouses.dashboard import render_warehouses_dashboard
from services.navigation_service import NAV_ALIAS_MAP, normalize_navigation_label


ROUTE_GROUPS = {
    "public": {"Dashboard"},
    "shared_authenticated": {"Dashboard", "My Profile", "Notifications", "My Actions"},
    ROLE_PLATFORM_ADMIN: {
        "Dashboard",
        "My Profile",
        "Notifications",
        "My Actions",
        "Manufacturers",
        "Mahajans",
        "Workers",
        "Products",
        "Product Approvals",
        "Marketplace",
        "Marketplace Orders",
        "MandiPlace",
        "Mandi Orders",
        "Raw Materials",
        "Supply Orders",
        "Payments",
        "Ledger",
        "Platform Commission",
        "Finance Operations",
        "Operations Center",
        "Warehouses",
        "Packaging Services",
        "Courier Services",
        "Shipments",
        "Logistics",
        "Jobs",
        "System Health",
        "Analytics",
    },
    ROLE_MAHAJAN: {"Dashboard", "My Profile", "Notifications", "My Actions", "Warehouses", "Raw Materials", "Shipments", "Mandi Orders", "Payments", "Ledger", "Jobs"},
    ROLE_MANUFACTURER: {"Dashboard", "My Profile", "Notifications", "My Actions", "Products", "Warehouses", "Inventory", "Shipments", "Marketplace", "Marketplace Orders", "MandiPlace", "Mandi Orders", "Supply Requests", "Suta Mandi", "Payments", "Ledger", "Jobs"},
    ROLE_PUBLIC_BUYER: {"Dashboard", "My Profile", "Notifications", "My Actions", "Marketplace", "Marketplace Orders", "Jobs"},
    ROLE_WORKER: {"Dashboard", "My Profile", "Notifications", "My Actions", "Jobs"},
}


def can_access_route(user, section: str, app_context: dict) -> bool:
    normalized_section = normalize_navigation_label(section)
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
        return normalized_section == "Dashboard"
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
    section = normalize_navigation_label(section)
    user = app_context.get("current_user")
    session_user = app_context.get("session_user") or user
    is_admin_identity = app_context["security_service"].is_admin_identity(session_user)
    supervisor_mode = bool(is_admin_identity and getattr(user, "role", "") == ROLE_PLATFORM_ADMIN)
    if not user:
        if section == "Marketplace":
            st.session_state["requested_role"] = ROLE_PUBLIC_BUYER
        render_login_page(app_context)
        return
    if not can_access_route(user, section, app_context):
        _render_access_denied(app_context)
        return
    if section == "Dashboard":
        render_dashboard(app_context)
    elif section == "My Actions":
        render_actions_dashboard(app_context)
    elif section == "Notifications":
        render_notifications_dashboard(app_context)
    elif section in {"My Profile", "Profile"}:
        render_my_profile_dashboard(app_context)
    elif section == "Products":
        render_products_dashboard(app_context)
    elif section == "MandiPlace":
        render_procurement_dashboard(app_context)
    elif section == "Suta Mandi":
        render_suta_mandi_dashboard(app_context)
    elif section in {"Marketplace", "Marketplace Preview"}:
        render_marketplace_dashboard(app_context)
    elif section in {"Marketplace Orders", "Public Orders"}:
        current_user = app_context.get("current_user")
        if current_user and current_user.role == ROLE_PUBLIC_BUYER:
            render_public_orders_dashboard(app_context, buyer_mode=True)
        elif current_user and current_user.role in {ROLE_MANUFACTURER, "admin_as_manufacturer"}:
            render_orders_dashboard(app_context)
        else:
            render_public_orders_dashboard(app_context, buyer_mode=False)
    elif section == "My Orders":
        current_user = app_context.get("current_user")
        if current_user and current_user.role == ROLE_PUBLIC_BUYER:
            render_public_orders_dashboard(app_context, buyer_mode=True)
        else:
            render_orders_dashboard(app_context)
    elif section == "Inventory":
        render_inventory_management(app_context)
    elif section == "Warehouses":
        render_warehouses_dashboard(app_context)
    elif section == "Shipments":
        render_shipments_dashboard(app_context)
    elif section in {"Supply Orders", "Supply Requests"}:
        render_procurement_dashboard(app_context)
    elif section == "Mandi Orders":
        if "procurement_transaction_service" in app_context:
            render_procurement_dashboard(app_context)
        elif supervisor_mode:
            render_admin_dashboard(app_context, section="Mandi Orders")
        else:
            _render_access_denied(app_context)
    elif section in {"Ledger / Khata", "Ledger"}:
        if supervisor_mode:
            render_admin_dashboard(app_context, section="Ledger")
        else:
            render_ledger_dashboard(app_context)
    elif section in {"Payments", "Platform Commission"}:
        if section == "Platform Commission" and supervisor_mode:
            render_commission_summary_dashboard(app_context)
        elif section == "Platform Commission":
            render_commission_dashboard(app_context)
        elif supervisor_mode:
            render_admin_dashboard(app_context, section="Payments")
        else:
            render_payments_dashboard(app_context)
    elif section == "Finance Operations":
        if "settlement_service" in app_context and "invoice_service" in app_context and "dispute_service" in app_context:
            render_finance_operations_dashboard(app_context)
        elif supervisor_mode:
            render_admin_dashboard(app_context, section="Finance Operations")
        else:
            _render_access_denied(app_context)
    elif section == "Dispatch":
        render_dispatch_management(app_context)
    elif section == "Mahajans":
        render_mahajans_dashboard(app_context)
    elif section == "Workers":
        render_workers_admin_dashboard(app_context)
    elif section == "Raw Materials":
        render_raw_materials_dashboard(app_context)
    elif section == "Operations Center":
        render_operations_dashboard(app_context)
    elif section == "Packaging Services":
        render_packaging_services_dashboard(app_context)
    elif section == "Courier Services":
        render_courier_services_dashboard(app_context)
    elif section == "Logistics":
        render_logistics_dashboard(app_context)
    elif section == "Jobs":
        render_jobs_dashboard(app_context)
    elif section == "Analytics":
        render_analytics_dashboard(app_context)
    elif section == "Product Approvals":
        render_product_approvals_dashboard(app_context)
    elif section == "Manufacturers":
        render_manufacturers_dashboard(app_context)
    elif section == "Inventory Summary":
        render_inventory_summary_dashboard(app_context)
    elif section in {"B2B Preview", "Ledger Summary", "Commission Summary"}:
        render_admin_dashboard(app_context, section=section)
    elif section == "Onboarding":
        render_manufacturer_onboarding(app_context)
    elif section == "System Health":
        render_health_dashboard(app_context)
