from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from services.master_data_service import MasterDataService

MASTER_DATA = MasterDataService()
CLIENT_STATUSES = ["INVITED", "ACTIVE", "INACTIVE", "BLOCKED"]


def _safe_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _client_form(*, key_prefix: str, defaults: dict | None = None) -> tuple[bool, dict]:
    defaults = defaults or {}
    address = defaults.get("address", {}) or {}
    delivery_contact = defaults.get("delivery_contact", {}) or {}
    states = MASTER_DATA.get_indian_states_and_union_territories()
    with st.form(f"{key_prefix}_client_form"):
        col1, col2 = st.columns(2)
        business_name = col1.text_input("Business Name", value=defaults.get("business_name", ""))
        owner_name = col2.text_input("Owner Name", value=defaults.get("owner_name", ""))
        email = col1.text_input("Email", value=defaults.get("email", ""))
        mobile = col2.text_input("Mobile Number", value=defaults.get("mobile", ""))
        alternate_mobile = col1.text_input("Alternate Mobile Number", value=defaults.get("alternate_mobile", ""))
        gstin = col2.text_input("GSTIN", value=defaults.get("gstin", ""))
        pan = col1.text_input("PAN", value=defaults.get("pan", ""))
        credit_limit = col2.number_input("Credit Limit", min_value=0, value=int(defaults.get("credit_limit", 0) or 0), step=1000)
        ledger_allowed = st.checkbox("Ledger Allowed", value=bool(defaults.get("ledger_allowed", True)))

        st.markdown("#### Address")
        line1 = st.text_input("Address Line 1", value=address.get("line1", ""))
        line2 = st.text_input("Address Line 2", value=address.get("line2", ""))
        city_col, state_col, pin_col = st.columns(3)
        city = city_col.text_input("City", value=address.get("city", ""))
        state = state_col.selectbox("State", states, index=_safe_index(states, address.get("state", "")))
        pin_code = pin_col.text_input("PIN Code", value=address.get("pin_code", ""))
        landmark = st.text_input("Landmark", value=address.get("landmark", ""))

        st.markdown("#### Delivery Contact")
        contact_col1, contact_col2 = st.columns(2)
        contact_name = contact_col1.text_input("Contact Name", value=delivery_contact.get("name", ""))
        contact_mobile = contact_col2.text_input("Contact Mobile", value=delivery_contact.get("mobile", ""))
        delivery_instructions = st.text_area("Delivery Instructions", value=defaults.get("delivery_instructions", ""), height=100)
        status = st.selectbox("Status", CLIENT_STATUSES, index=_safe_index(CLIENT_STATUSES, defaults.get("status", "INVITED")))
        submitted = st.form_submit_button("Save Client")

    return submitted, {
        "business_name": business_name.strip(),
        "owner_name": owner_name.strip(),
        "email": email.strip().lower(),
        "mobile": mobile.strip(),
        "alternate_mobile": alternate_mobile.strip(),
        "gstin": gstin.strip(),
        "pan": pan.strip(),
        "credit_limit": int(credit_limit),
        "ledger_allowed": ledger_allowed,
        "status": status,
        "address": {
            "line1": line1.strip(),
            "line2": line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
            "landmark": landmark.strip(),
        },
        "delivery_contact": {"name": contact_name.strip(), "mobile": contact_mobile.strip()},
        "delivery_instructions": delivery_instructions.strip(),
    }


def render_clients_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Clients", "Create, manage, invite, and control your manufacturer-specific private client network here.", ["Private Clients", "Manufacturer Workspace"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return

    client_service = app_context["client_service"]
    governance_service = app_context["governance_service"]
    manufacturer = governance_service.get_manufacturer(user.manufacturer_code) or {}
    clients = client_service.list_clients(user.manufacturer_code)
    render_metric_grid(
        [
            render_metric_card("Clients", str(len(clients)), "SUCCESS"),
            render_metric_card("Active", str(len([item for item in clients if item.get("status") == "ACTIVE"])), "OPEN"),
            render_metric_card("Invites Sent", str(len([item for item in clients if item.get("invite_status") == "SENT"])), "PENDING"),
        ]
    )

    overview_tab, create_tab, manage_tab = st.tabs(["Overview", "Create Client", "Manage Clients"])
    with overview_tab:
        render_section_intro("Client Network", "This registry is private to the current manufacturer. Other manufacturers and public buyers cannot access it.")
        st.dataframe(clients, use_container_width=True)

    with create_tab:
        submitted, payload = _client_form(key_prefix="create_client")
        if submitted:
            try:
                client = client_service.create_client(user.manufacturer_code, payload)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Client {client['client_id']} created.")
                st.rerun()

    with manage_tab:
        if not clients:
            st.info("No clients created yet.")
            return
        selected_id = st.selectbox("Select Client", [item["client_id"] for item in clients])
        selected = next(item for item in clients if item["client_id"] == selected_id)
        submitted, payload = _client_form(key_prefix=f"edit_{selected_id}", defaults=selected)
        if submitted:
            try:
                client_service.update_client(user.manufacturer_code, selected_id, payload)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"{selected_id} updated.")
                st.rerun()

        col1, col2 = st.columns(2)
        if col1.button("Deactivate Client", use_container_width=True):
            client_service.deactivate_client(user.manufacturer_code, selected_id)
            st.success(f"{selected_id} deactivated.")
            st.rerun()
        if col2.button("Send Gmail Invite", use_container_width=True):
            updated = client_service.send_invitation(
                user.manufacturer_code,
                selected_id,
                manufacturer.get("business_name", user.manufacturer_code),
                "Open the MandiTrade app and continue with Google sign-in.",
            )
            if updated.get("invite_status") == "FAILED":
                st.error("Invite failed. Check Gmail runtime logs.")
            else:
                st.success(f"Invite sent to {updated['email']}.")
            st.rerun()
