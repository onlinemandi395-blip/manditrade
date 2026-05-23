from __future__ import annotations

from collections import Counter

import streamlit as st


def render_analytics_dashboard(app_context: dict) -> None:
    st.subheader("Analytics")
    current_user = app_context["current_user"]
    governance_service = app_context["governance_service"]

    if current_user and current_user.role == "manufacturer" and current_user.manufacturer_code:
        orders = app_context["order_query_service"].list_orders(current_user.manufacturer_code)
        procurement = app_context["procurement_query_service"].list_procurement_requests(current_user.manufacturer_code)
        inventory = app_context["inventory_query_service"].list_inventory_snapshot(current_user.manufacturer_code)
        top_products = Counter()
        for order in orders:
            for item in order.get("items", []):
                top_products[item.get("product_name", item.get("product_id", ""))] += int(item.get("qty", 0))
        col1, col2, col3 = st.columns(3)
        col1.metric("Order Volume", len(orders))
        col2.metric("Procurement Volume", len(procurement))
        col3.metric("Inventory Movements", len(inventory.get("items", [])))
        st.dataframe([{"product": k, "ordered_qty": v} for k, v in top_products.most_common(10)], use_container_width=True)
        return

    manufacturers = governance_service.list_manufacturers()
    products = governance_service.list_products()
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Manufacturers", len([m for m in manufacturers if m.get("status") == "approved"]))
    col2.metric("Pending Approvals", len([m for m in manufacturers if m.get("status") == "pending_approval"]))
    col3.metric("Product Registry", len(products))
    st.caption("Admin analytics exclude private client identities and invoice data.")
