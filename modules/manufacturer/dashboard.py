from __future__ import annotations

import streamlit as st


def render_manufacturer_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    st.subheader("Manufacturer Dashboard")
    st.caption("Digital Bharat Mandi + Khata + RFQ + Inventory + Client Network")
    if not user or not user.manufacturer_code:
        st.info("Sign in as a manufacturer to view workspace details.")
        return
    inventory = app_context["dual_inventory_service"].list_inventory(user.manufacturer_code)
    orders = app_context["order_query_service"].list_orders(user.manufacturer_code)
    rfqs = app_context["procurement_query_service"].list_procurement_requests(user.manufacturer_code)
    ledgers = app_context["ledger_service"].list_ledgers(user.manufacturer_code)
    self_available = sum(int(item.get("self_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))
    mandi_available = sum(int(item.get("mandi_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Self Inventory", self_available)
    col2.metric("Mandi Inventory", mandi_available)
    col3.metric("Client Orders", len(orders))
    col4.metric("Open RFQs", len([item for item in rfqs if item.get("status") == "OPEN"]))

    st.markdown("### Recent Ledgers")
    st.dataframe(ledgers, use_container_width=True)
