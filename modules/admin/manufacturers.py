from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from services.master_data_service import MasterDataService

BUSINESS_TYPES = [
    "Manufacturer",
    "Trader",
    "Wholesaler",
    "Processor",
    "Distributor",
    "Other",
]
SUBSCRIPTION_PLANS = ["Basic", "Premium", "Premium+"]
MASTER_DATA = MasterDataService()


def _address_of(manufacturer: dict) -> dict:
    address = manufacturer.get("address", {}) or {}
    return {
        "line1": address.get("line1", ""),
        "line2": address.get("line2", ""),
        "city": address.get("city", manufacturer.get("city", "")),
        "state": address.get("state", ""),
        "pin_code": address.get("pin_code", ""),
    }


def _legal_of(manufacturer: dict) -> dict:
    return manufacturer.get("legal", {}) or {}


def _banking_of(manufacturer: dict) -> dict:
    return manufacturer.get("banking", {}) or {}


def _categories_text(manufacturer: dict) -> str:
    return ", ".join(manufacturer.get("product_categories", []) or [])


def _option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _subscription_plan_index(value: str) -> int:
    normalized = (value or "").strip().lower()
    mapping = {
        "basic": "Basic",
        "premium": "Premium",
        "premium+": "Premium+",
    }
    return _option_index(SUBSCRIPTION_PLANS, mapping.get(normalized, value))


def _safe_multiselect_defaults(options: list[str], values: list[str]) -> list[str]:
    allowed = set(options)
    return [item for item in values if item in allowed]


def _render_manufacturer_details_form(*, prefix: str, defaults: dict, include_status: bool, submit_label: str) -> tuple[bool, dict]:
    address = _address_of(defaults)
    legal = _legal_of(defaults)
    banking = _banking_of(defaults)
    business_type = defaults.get("business_type") or BUSINESS_TYPES[0]
    status = defaults.get("status", "ACTIVE")
    subscription_plan = defaults.get("subscription_plan", "basic")
    states = MASTER_DATA.get_indian_states_and_union_territories()
    categories = MASTER_DATA.get_product_categories()

    with st.form(f"{prefix}_manufacturer_crud_form"):
        code_col, plan_col = st.columns(2)
        manufacturer_code = code_col.text_input("Manufacturer Code", value=defaults.get("manufacturer_code", ""), disabled=True)
        selected_plan = plan_col.selectbox("Subscription Plan", SUBSCRIPTION_PLANS, index=_subscription_plan_index(subscription_plan))

        col1, col2 = st.columns(2)
        business_name = col1.text_input("Business / Manufacturer Name", value=defaults.get("business_name", defaults.get("manufacturer_name", "")))
        owner_name = col2.text_input("Owner Name", value=defaults.get("owner_name", ""))
        owner_email = col1.text_input("Owner Email", value=defaults.get("owner_email", ""))
        mobile = col2.text_input("Mobile Number", value=defaults.get("mobile", ""))
        alternate_mobile = col1.text_input("Alternate Mobile Number", value=defaults.get("alternate_mobile", ""))
        business_type_value = col2.selectbox("Business Type", BUSINESS_TYPES, index=_option_index(BUSINESS_TYPES, business_type))

        st.markdown("#### Address")
        address_line1 = st.text_input("Full Address", value=address.get("line1", ""))
        address_line2 = st.text_input("Address Line 2", value=address.get("line2", ""))
        city_col, state_col, pin_col = st.columns(3)
        city = city_col.text_input("City", value=address.get("city", ""))
        state = state_col.selectbox("State", states, index=_option_index(states, address.get("state", "")))
        pin_code = pin_col.text_input("PIN Code", value=address.get("pin_code", ""))

        product_categories = st.multiselect(
            "Product Categories",
            categories,
            default=_safe_multiselect_defaults(categories, defaults.get("product_categories", []) or []),
        )

        st.markdown("#### Legal Details")
        legal_col1, legal_col2 = st.columns(2)
        udyam_id = legal_col1.text_input("Udyam Registration Number", value=legal.get("udyam_id", ""))
        gstin = legal_col2.text_input("GSTIN", value=legal.get("gstin", ""))
        pan = legal_col1.text_input("PAN Number", value=legal.get("pan", ""))
        aadhaar = legal_col2.text_input("Aadhaar Number", value=legal.get("aadhaar", ""))

        st.markdown("#### Banking Details")
        bank_col1, bank_col2 = st.columns(2)
        account_holder_name = bank_col1.text_input("Bank Account Holder Name", value=banking.get("account_holder_name", ""))
        account_number = bank_col2.text_input("Bank Account Number", value=banking.get("account_number", ""))
        ifsc_code = bank_col1.text_input("IFSC Code", value=banking.get("ifsc", ""))
        upi_id = bank_col2.text_input("UPI ID", value=banking.get("upi_id", ""))

        status_col, _spacer = st.columns(2)
        selected_status = "ACTIVE"
        if include_status:
            selected_status = status_col.selectbox("Lifecycle Status", ["ACTIVE", "INACTIVE", "BLOCKED"], index=_option_index(["ACTIVE", "INACTIVE", "BLOCKED"], status))
        business_description = st.text_area("Business Description", value=defaults.get("business_description", ""), height=120)
        submitted = st.form_submit_button(submit_label)

    payload = {
        "manufacturer_code": manufacturer_code.strip().upper(),
        "manufacturer_name": business_name.strip(),
        "business_name": business_name.strip(),
        "owner_name": owner_name.strip(),
        "owner_email": owner_email.strip(),
        "mobile": mobile.strip(),
        "alternate_mobile": alternate_mobile.strip(),
        "address": {
            "line1": address_line1.strip(),
            "line2": address_line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
        },
        "city": city.strip(),
        "state": state.strip(),
        "pin_code": pin_code.strip(),
        "business_type": business_type_value.strip(),
        "product_categories": product_categories,
        "legal": {
            "udyam_id": udyam_id.strip(),
            "gstin": gstin.strip(),
            "pan": pan.strip(),
            "aadhaar": aadhaar.strip(),
        },
        "banking": {
            "account_holder_name": account_holder_name.strip(),
            "account_number": account_number.strip(),
            "ifsc": ifsc_code.strip(),
            "upi_id": upi_id.strip(),
        },
        "business_description": business_description.strip(),
        "subscription_plan": selected_plan.strip(),
        "status": selected_status.strip(),
    }
    return submitted, payload


def render_manufacturers_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    onboarding_service = app_context["manufacturer_onboarding_service"]
    current_user = app_context["current_user"]
    manufacturers = governance_service.list_manufacturers()

    render_page_header(
        "Manufacturers",
        "Platform admin can create, review, update, and delete manufacturer registry details from this page.",
        ["Platform Admin", "Registry CRUD"],
    )
    render_metric_grid(
        [
            render_metric_card("Active", str(len([item for item in manufacturers if item.get("status") == "ACTIVE"])), "SUCCESS"),
            render_metric_card("Blocked", str(len([item for item in manufacturers if item.get("status") == "BLOCKED"])), "WARNING"),
            render_metric_card("Inactive", str(len([item for item in manufacturers if item.get("status") == "INACTIVE"])), "PENDING"),
        ]
    )
    overview_tab, create_tab, manage_tab, packet_tab = st.tabs(["Overview", "Create", "Manage", "Onboarding Packet"])
    with overview_tab:
        render_section_intro("Registry CRUD", "Create new manufacturers here, update full business details, and remove registry entries when needed.")
        st.markdown("### Registered Manufacturers")
        st.dataframe(manufacturers, use_container_width=True)
    with create_tab:
        st.markdown("### Create Manufacturer")
        generated_code = onboarding_service.generate_next_manufacturer_code()
        create_submitted, create_payload = _render_manufacturer_details_form(
            prefix="admin_create_manufacturer",
            defaults={"manufacturer_code": generated_code},
            include_status=False,
            submit_label="Create Manufacturer",
        )
        if create_submitted:
            try:
                created = onboarding_service.create_manufacturer(
                    manufacturer_code=create_payload["manufacturer_code"],
                    manufacturer_name=create_payload["business_name"],
                    business_name=create_payload["business_name"],
                    owner_name=create_payload["owner_name"],
                    owner_email=create_payload["owner_email"],
                    mobile=create_payload["mobile"],
                    alternate_mobile=create_payload["alternate_mobile"],
                    address_line1=create_payload["address"]["line1"],
                    address_line2=create_payload["address"]["line2"],
                    city=create_payload["address"]["city"],
                    state=create_payload["address"]["state"],
                    pin_code=create_payload["address"]["pin_code"],
                    business_type=create_payload["business_type"],
                    product_categories=create_payload["product_categories"],
                    udyam_id=create_payload["legal"]["udyam_id"],
                    gstin=create_payload["legal"]["gstin"],
                    pan=create_payload["legal"]["pan"],
                    aadhaar=create_payload["legal"]["aadhaar"],
                    bank_account_holder_name=create_payload["banking"]["account_holder_name"],
                    bank_account_number=create_payload["banking"]["account_number"],
                    ifsc_code=create_payload["banking"]["ifsc"],
                    upi_id=create_payload["banking"]["upi_id"],
                    business_description=create_payload["business_description"],
                    created_by=current_user.email if current_user else "system",
                    subscription_plan=create_payload["subscription_plan"],
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Manufacturer {created['manufacturer_code']} created.")
                st.rerun()

    if not manufacturers:
        with manage_tab:
            st.info("No manufacturers are registered yet.")
        with packet_tab:
            st.info("Create a manufacturer first to view an onboarding packet.")
        return

    selected_code = next(item["manufacturer_code"] for item in manufacturers)
    with manage_tab:
        selected_code = st.selectbox("Manage Manufacturer", [item["manufacturer_code"] for item in manufacturers], key="manage_manufacturer_select")
        selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)
        st.markdown("### Update Manufacturer Details")
        update_submitted, update_payload = _render_manufacturer_details_form(
            prefix=f"admin_update_{selected_code}",
            defaults=selected,
            include_status=True,
            submit_label="Save Manufacturer Details",
        )
        if update_submitted:
            try:
                onboarding_service.update_manufacturer(selected_code, update_payload)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"{selected_code} updated.")
                st.rerun()

        col_a, col_b = st.columns(2)
        if col_a.button("Regenerate Onboarding Secret", use_container_width=True):
            refreshed = onboarding_service.regenerate_secret(selected_code)
            st.success("Onboarding secret regenerated.")
            st.code(refreshed["manufacturer_onboarding_steps"], language="text")
            st.rerun()
        if col_b.button("Delete Manufacturer Registry Entry", use_container_width=True):
            onboarding_service.delete_manufacturer(selected_code, remove_workspace=False)
            st.success(f"{selected_code} removed from registry.")
            st.rerun()

    with packet_tab:
        selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)
        st.markdown("### Shareable Onboarding Packet")
        st.code(selected.get("manufacturer_onboarding_steps", ""), language="text")
