from __future__ import annotations

import streamlit as st

from modules.access.dashboard import render_access_portal, render_pending_user_dashboard
from modules.actions.dashboard import render_actions_dashboard
from modules.admin.dashboard import render_admin_dashboard
from modules.admin.manufacturers import render_manufacturers_dashboard
from modules.admin.product_approvals import render_product_approvals_dashboard
from modules.client.dashboard import render_client_dashboard
from modules.clients.dashboard import render_clients_dashboard
from modules.inventory.management import render_inventory_management
from modules.jobs.dashboard import render_jobs_dashboard
from modules.ledger.dashboard import render_ledger_dashboard
from modules.manufacturer.dashboard import render_manufacturer_dashboard
from modules.notifications.dashboard import render_notifications_dashboard
from modules.onboarding.manufacturer_onboarding import render_manufacturer_onboarding
from modules.orders.dashboard import render_orders_dashboard
from modules.orders.dispatch import render_dispatch_management
from modules.payments.dashboard import render_payments_dashboard
from modules.products.dashboard import render_products_dashboard
from modules.rfq.dashboard import render_rfq_dashboard
from modules.system.health_dashboard import render_health_dashboard
from modules.workers.dashboard import render_workers_dashboard


def render_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    if not user:
        render_access_portal(app_context)
        return
    if user.role in {"admin", "platform_admin"}:
        render_admin_dashboard(app_context)
    elif user.role in {"manufacturer", "admin_as_manufacturer"}:
        render_manufacturer_dashboard(app_context)
    elif user.role == "worker":
        render_workers_dashboard(app_context)
    elif user.role == "pending_user":
        render_pending_user_dashboard(app_context)
    else:
        render_client_dashboard(app_context)


def render_route(section: str, app_context: dict) -> None:
    if section == "Dashboard":
        render_dashboard(app_context)
    elif section == "My Actions":
        render_actions_dashboard(app_context)
    elif section == "Notifications":
        render_notifications_dashboard(app_context)
    elif section == "Products":
        render_products_dashboard(app_context)
    elif section == "Inventory":
        render_inventory_management(app_context)
    elif section == "Client Orders":
        render_orders_dashboard(app_context)
    elif section == "Mandi RFQ":
        render_rfq_dashboard(app_context)
    elif section == "Ledger / Khata":
        render_ledger_dashboard(app_context)
    elif section == "Payments":
        render_payments_dashboard(app_context)
    elif section == "Dispatch":
        render_dispatch_management(app_context)
    elif section == "Clients":
        render_clients_dashboard(app_context)
    elif section == "Jobs in Mandi":
        render_jobs_dashboard(app_context)
    elif section == "Workers":
        render_workers_dashboard(app_context)
    elif section == "Product Approvals":
        render_product_approvals_dashboard(app_context)
    elif section == "Manufacturers":
        render_manufacturers_dashboard(app_context)
    elif section == "Onboarding":
        render_manufacturer_onboarding(app_context)
    elif section == "System Health":
        render_health_dashboard(app_context)
