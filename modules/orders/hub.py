from __future__ import annotations

import streamlit as st

from components.data_grid import render_data_grid
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def _status_bucket(rows: list[dict], statuses: set[str]) -> list[dict]:
    return [item for item in rows if str(item.get("status", "")).strip().upper() in statuses]


def _render_registry(page_key: str, rows: list[dict], *, search_fields: list[str]) -> None:
    if not rows:
        st.info("No records available in this view yet.")
        return
    render_data_grid(
        page_key=page_key,
        rows=rows,
        search_fields=search_fields,
        status_field="status",
        date_field="updated_at",
        search_placeholder="Search orders",
    )


def render_orders_hub(app_context: dict) -> None:
    public_order_service = app_context["public_order_service"]
    procurement_service = app_context["procurement_transaction_service"]
    marketplace_orders = public_order_service.list_all_orders()
    mandiplace_orders = procurement_service.list_mandiplace_orders()
    supply_orders = procurement_service.list_supply_orders()
    suta_orders = [item for item in supply_orders if str(item.get("network", "")).strip().upper() == "SUTA_MANDI" or "suta" in str(item.get("category", "")).lower()]
    combined_orders = marketplace_orders + mandiplace_orders + supply_orders
    completed_statuses = {"DELIVERED", "RECEIVED", "CLOSED"}
    cancelled_statuses = {"CANCELLED"}
    render_page_header(
        "Orders",
        "Use one consolidated operations page to inspect marketplace, MandiPlace, raw-material, and suta order lanes without hunting across the sidebar.",
        ["Admin Orders", "Consolidated View"],
        role="Platform Admin",
        metrics=[
            ("Marketplace", str(len(marketplace_orders))),
            ("MandiPlace", str(len(mandiplace_orders))),
            ("Supply", str(len(supply_orders))),
        ],
        kicker="Orders Control Deck",
    )
    render_metric_grid(
        [
            render_metric_card("Open Orders", str(len([item for item in combined_orders if str(item.get("status", "")).strip().upper() not in completed_statuses | cancelled_statuses])), "OPEN"),
            render_metric_card("In Progress", str(len([item for item in combined_orders if str(item.get("status", "")).strip().upper() in {"PENDING", "CONFIRMED", "ASSIGNED", "DISPATCHED", "IN_TRANSIT"}])), "PENDING"),
            render_metric_card("Delivered", str(len(_status_bucket(combined_orders, completed_statuses))), "SUCCESS"),
            render_metric_card("Cancelled", str(len(_status_bucket(combined_orders, cancelled_statuses))), "WARNING"),
        ]
    )
    render_section_intro("Order Lanes", "Marketplace and procurement orders stay in their existing business flows, but this page gives admin one visible entry point.")
    marketplace_tab, mandiplace_tab, raw_materials_tab, suta_tab, completed_tab, cancelled_tab = st.tabs(
        ["Marketplace Orders", "MandiPlace Orders", "Raw Material Orders", "Suta Orders", "Completed", "Cancelled"]
    )
    with marketplace_tab:
        _render_registry("orders_marketplace", marketplace_orders, search_fields=["public_order_id", "buyer_email", "assigned_seller_manufacturer_id"])
    with mandiplace_tab:
        _render_registry("orders_mandiplace", mandiplace_orders, search_fields=["mandiplace_order_id", "requesting_manufacturer_id", "supplier_manufacturer_id"])
    with raw_materials_tab:
        _render_registry("orders_supply", supply_orders, search_fields=["mandi_order_id", "manufacturer_id", "mahajan_id", "raw_material_id"])
    with suta_tab:
        _render_registry("orders_suta", suta_orders, search_fields=["mandi_order_id", "manufacturer_id", "mahajan_id"])
    with completed_tab:
        _render_registry("orders_completed", _status_bucket(combined_orders, completed_statuses), search_fields=["public_order_id", "mandiplace_order_id", "mandi_order_id"])
    with cancelled_tab:
        _render_registry("orders_cancelled", _status_bucket(combined_orders, cancelled_statuses), search_fields=["public_order_id", "mandiplace_order_id", "mandi_order_id"])


def render_my_orders_hub(app_context: dict) -> None:
    user = app_context["current_user"]
    if not user:
        st.info("Sign in to view your orders.")
        return
    public_order_service = app_context["public_order_service"]
    procurement_service = app_context["procurement_transaction_service"]
    role = str(user.role or "").strip().lower()
    if role == "public_buyer":
        from modules.public_orders.dashboard import render_public_orders_dashboard

        render_public_orders_dashboard(app_context, buyer_mode=True)
        return
    if role in {"manufacturer", "admin_as_manufacturer"}:
        manufacturer_code = user.manufacturer_code or ""
        marketplace_orders = app_context["order_query_service"].list_orders(manufacturer_code)
        mandiplace_orders = procurement_service.list_mandiplace_orders(manufacturer_code=manufacturer_code)
        supply_orders = procurement_service.list_supply_orders(manufacturer_code=manufacturer_code)
        suta_orders = [item for item in supply_orders if str(item.get("network", "")).strip().upper() == "SUTA_MANDI" or "suta" in str(item.get("category", "")).lower()]
        render_page_header(
            "My Orders",
            "Track seller-side marketplace orders together with MandiPlace, raw-material, and suta procurement from one route.",
            ["Manufacturer Workspace", "Order Hub"],
            role="Manufacturer",
            kicker="Unified Order Desk",
        )
        tabs = st.tabs(["Marketplace Orders", "MandiPlace Orders", "Raw Material Orders", "Suta Orders"])
        with tabs[0]:
            _render_registry("my_orders_marketplace", marketplace_orders, search_fields=["public_order_id", "status"])
        with tabs[1]:
            _render_registry("my_orders_mandiplace", mandiplace_orders, search_fields=["mandiplace_order_id", "status"])
        with tabs[2]:
            _render_registry("my_orders_supply", supply_orders, search_fields=["mandi_order_id", "status", "raw_material_id"])
        with tabs[3]:
            _render_registry("my_orders_suta", suta_orders, search_fields=["mandi_order_id", "status"])
        return
    if role == "mahajan":
        mahajan = app_context["governance_service"].get_mahajan_by_email(user.email)
        orders = procurement_service.list_supply_orders(mahajan_id=(mahajan or {}).get("mahajan_id"))
        render_page_header(
            "My Orders",
            "Track assigned supply orders, confirmations, dispatches, and deliveries from one mahajan-facing route.",
            ["Mahajan Workspace", "Supply Orders"],
            role="Mahajan",
            kicker="Supply Desk",
        )
        overview_tab, registry_tab = st.tabs(["Overview", "Orders"])
        with overview_tab:
            render_metric_grid(
                [
                    render_metric_card("Assigned", str(len([item for item in orders if str(item.get("status", "")).strip().upper() in {"REQUESTED", "QUOTED", "SUPPLIER_ASSIGNED"}])), "PENDING"),
                    render_metric_card("Confirmed", str(len([item for item in orders if str(item.get("status", "")).strip().upper() == "CONFIRMED"])), "OPEN"),
                    render_metric_card("Delivered", str(len([item for item in orders if str(item.get("status", "")).strip().upper() in {"DELIVERED", "RECEIVED"}])), "SUCCESS"),
                ]
            )
        with registry_tab:
            _render_registry("my_orders_mahajan", orders, search_fields=["mandi_order_id", "manufacturer_id", "status"])
        return
    st.info("This route is currently reserved for marketplace buyers, manufacturers, and mahajans.")
