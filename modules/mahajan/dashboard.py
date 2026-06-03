from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip
from utils.page_ui import render_metric_button_row


def render_mahajan_dashboard(app_context: dict) -> None:
    user = app_context.get("current_user")
    governance_service = app_context["governance_service"]
    procurement_service = app_context["procurement_transaction_service"]

    render_page_header(
        "Mahajan Supply Dashboard",
        "Read-only supply overview for admin-linked raw materials, assigned mandi orders, dispatch status, and finance visibility.",
        ["Read Only", "Supply Network"],
        role=(user.role if user else "mahajan").replace("_", " ").title(),
    )

    mahajan = governance_service.get_mahajan_by_email(user.email) if user else None
    if not mahajan:
        st.info("Your mahajan profile is not linked yet. Ask admin to activate your supplier record.")
        return

    mahajan_id = mahajan.get("mahajan_id", "")
    raw_materials = [item for item in governance_service.list_raw_materials() if item.get("mahajan_id") == mahajan_id]
    supply_orders = procurement_service.list_supply_orders(mahajan_id=mahajan_id)
    active_orders = [item for item in supply_orders if item.get("status") not in {"CLOSED", "CANCELLED"}]
    quoted_orders = [item for item in supply_orders if item.get("status") == "MAHAJAN_QUOTED"]
    dispatched_orders = [item for item in supply_orders if item.get("status") == "MAHAJAN_DISPATCHED"]

    render_metric_grid(
        [
            render_metric_card("Raw Materials", str(len(raw_materials)), "SUCCESS"),
            render_metric_card("Active Supply Orders", str(len(active_orders)), "OPEN"),
            render_metric_card("Quoted Orders", str(len(quoted_orders)), "PENDING"),
            render_metric_card("Dispatched", str(len(dispatched_orders)), "WARNING"),
        ]
    )
    render_showcase_strip(
        [
            ("Catalog Status", mahajan.get("status", "ACTIVE"), "SUCCESS"),
            ("Marketplace Access", "Restricted", "WARNING"),
            ("Supply Scope", "Admin Linked", "OPEN"),
        ]
    )
    render_metric_button_row(
        "mahajan_dashboard",
        [
            {"label": "Overview", "value": str(len(active_orders)), "tab_name": "Overview"},
            {"label": "Catalog", "value": str(len(raw_materials)), "tab_name": "Catalog"},
            {"label": "Orders", "value": str(len(supply_orders)), "tab_name": "Orders"},
            {"label": "Finance", "value": str(len(quoted_orders)), "tab_name": "Finance"},
        ],
    )
    render_section_intro(
        "Read-Only Supply View",
        "This dashboard is summary-only. Use Raw Materials, Mandi Orders, Payments, and Ledger to take operational actions.",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Supply Pipeline")
        st.bar_chart(
            {
                "Active": len(active_orders),
                "Quoted": len(quoted_orders),
                "Dispatched": len(dispatched_orders),
            }
        )
    with col2:
        st.markdown("#### Catalog Snapshot")
        category_counts: dict[str, int] = {}
        for item in raw_materials:
            category = str(item.get("category", "RAW_MATERIAL"))
            category_counts[category] = category_counts.get(category, 0) + 1
        st.bar_chart(category_counts or {"No Catalog": 0})

    overview_tab, catalog_tab, orders_tab, finance_tab = st.tabs(["Overview", "Catalog", "Orders", "Finance"])
    with overview_tab:
        st.dataframe(
            [
                {
                    "mahajan_id": mahajan_id,
                    "business_name": mahajan.get("business_name", ""),
                    "raw_materials": len(raw_materials),
                    "active_supply_orders": len(active_orders),
                    "quoted_orders": len(quoted_orders),
                    "dispatched_orders": len(dispatched_orders),
                }
            ],
            use_container_width=True,
        )
    with catalog_tab:
        st.dataframe(raw_materials, use_container_width=True)
    with orders_tab:
        st.dataframe(supply_orders, use_container_width=True)
    with finance_tab:
        st.dataframe(
            [
                {
                    "mandi_order_id": item.get("mandi_order_id", ""),
                    "status": item.get("status", ""),
                    "mahajan_unit_price": item.get("mahajan_unit_price", 0),
                    "manufacturer_unit_price": item.get("manufacturer_unit_price", 0),
                }
                for item in supply_orders
            ],
            use_container_width=True,
        )
