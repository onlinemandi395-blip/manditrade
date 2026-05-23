from __future__ import annotations

import streamlit as st

from services.json_service import JsonService


def render_manufacturer_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    st.subheader("Manufacturer Dashboard")
    st.caption("Inventory, clients, and agreements inside manufacturer-owned storage.")

    if not user or not user.manufacturer_code:
        st.info("Sign in as a manufacturer to view workspace details.")
        return

    drive_service = app_context["drive_service"]
    client_service = app_context["client_service"]
    order_query_service = app_context["order_query_service"]
    inventory_query_service = app_context["inventory_query_service"]
    procurement_query_service = app_context["procurement_query_service"]
    agreement_query_service = app_context["agreement_query_service"]
    json_service = JsonService()
    paths = drive_service.get_manufacturer_paths(user.manufacturer_code)
    inventory = inventory_query_service.list_inventory_snapshot(user.manufacturer_code)
    clients = client_service.list_clients(user.manufacturer_code)
    procurement = {"requests": procurement_query_service.list_procurement_requests(user.manufacturer_code)}
    agreements = {"agreements": agreement_query_service.list_agreements(user.manufacturer_code)}
    orders = order_query_service.list_orders(user.manufacturer_code)
    reserved_qty = sum(int(item.get("reserved_quantity", 0)) for item in inventory.get("items", []))
    pending_agreements = len([item for item in agreements.get("agreements", []) if item.get("status") in {"DRAFT", "ADVANCE_PENDING", "ACCEPTED"}])

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Manufacturer Code", user.manufacturer_code)
    col2.metric("Active Orders", len([item for item in orders if item.get("status") not in {"CLOSED"}]))
    col3.metric("Reserved Inventory", reserved_qty)
    col4.metric("Procurement Requests", len([item for item in procurement.get("requests", []) if item.get("status") == "OPEN"]))
    col5.metric("Pending Agreements", pending_agreements)

    st.metric("Client Count", len(clients))

    st.markdown("### Workspace Boundaries")
    st.code(f"Shared Zone: {paths.shared_zone}\nPrivate Zone: {paths.private_zone}", language="text")

    st.markdown("### Invite Client")
    with st.form("invite_client_form"):
        invite_email = st.text_input("Client Email")
        business_name = st.text_input("Business Name")
        invite_submit = st.form_submit_button("Send Invitation")

    if invite_submit and invite_email and business_name:
        invite = client_service.create_invite(user.manufacturer_code, invite_email.strip(), business_name.strip())
        client_service.send_invitation(invite)
        app_context["audit_service"].log_event(
            "client_invited",
            actor=user.email,
            details={"client_id": invite["client_id"], "email": invite["email"]},
        )
        st.success(f"Invitation queued for {invite_email}.")

    st.markdown("### Clients")
    st.dataframe(clients, use_container_width=True)
