from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip
from utils.page_ui import render_metric_button_row


def render_public_buyer_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    public_order_service = app_context.get("public_order_service")
    favorites_service = app_context.get("favorites_service")
    governance_service = app_context.get("governance_service")

    render_page_header(
        "Buyer Dashboard",
        "Read-only shopping overview for favorites, marketplace orders, delivery progress, and catalog breadth.",
        ["Read Only", "Marketplace"],
    )

    buyer_id = getattr(user, "public_buyer_id", "") or user.email
    orders = public_order_service.list_orders_for_buyer(buyer_id) if public_order_service and buyer_id else []
    favorites = favorites_service.list_favorites("public_buyer", buyer_id) if favorites_service and buyer_id else []
    products = [item for item in governance_service.list_products() if item.get("status") == "ACTIVE"] if governance_service else []
    open_orders = [item for item in orders if item.get("status") not in {"DELIVERED", "CANCELLED"}]
    delivered_orders = [item for item in orders if item.get("status") == "DELIVERED"]

    render_metric_grid(
        [
            render_metric_card("Active Products", str(len(products)), "SUCCESS"),
            render_metric_card("My Orders", str(len(orders)), "OPEN"),
            render_metric_card("Open Deliveries", str(len(open_orders)), "PENDING"),
            render_metric_card("Favorites", str(len(favorites)), "WARNING"),
        ]
    )
    render_showcase_strip(
        [
            ("Delivered Orders", str(len(delivered_orders)), "SUCCESS"),
            ("Payment Mode", "Manual / Verified", "OPEN"),
            ("Buying Surface", "Marketplace", "SUCCESS"),
        ]
    )
    render_metric_button_row(
        "public_buyer_dashboard",
        [
            {"label": "Overview", "value": str(len(products)), "tab_name": "Overview"},
            {"label": "Orders", "value": str(len(orders)), "tab_name": "Orders"},
            {"label": "Favorites", "value": str(len(favorites)), "tab_name": "Favorites"},
        ],
    )
    render_section_intro(
        "Read-Only Buyer View",
        "This dashboard is summary-only. Use Marketplace, Marketplace Orders, My Profile, and Notifications for shopping and account actions.",
    )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Order Snapshot")
        st.bar_chart(
            {
                "Total Orders": len(orders),
                "Open Deliveries": len(open_orders),
                "Delivered": len(delivered_orders),
            }
        )
    with col2:
        st.markdown("#### Interest Snapshot")
        st.bar_chart(
            {
                "Favorites": len(favorites),
                "Active Products": len(products),
            }
        )

    overview_tab, orders_tab, favorites_tab = st.tabs(["Overview", "Orders", "Favorites"])
    with overview_tab:
        st.dataframe(
            [
                {
                    "buyer_id": buyer_id,
                    "active_products": len(products),
                    "orders": len(orders),
                    "open_deliveries": len(open_orders),
                    "favorites": len(favorites),
                }
            ],
            use_container_width=True,
        )
    with orders_tab:
        st.dataframe(orders, use_container_width=True)
    with favorites_tab:
        st.dataframe(favorites, use_container_width=True)
