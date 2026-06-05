from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_mobile_record_card, render_page_header
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
PENDING_CREATE_CODE_KEY = "_pending_manufacturer_create_code"
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
    display_value = mapping.get(normalized, value)
    return _option_index(SUBSCRIPTION_PLANS, display_value)


def _safe_multiselect_defaults(options: list[str], values: list[str]) -> list[str]:
    allowed = set(options)
    return [item for item in values if item in allowed]


def _render_profile_form(*, prefix: str, defaults: dict, submit_label: str) -> tuple[bool, dict]:
    address = _address_of(defaults)
    legal = _legal_of(defaults)
    banking = _banking_of(defaults)
    business_type = defaults.get("business_type") or BUSINESS_TYPES[0]
    states = MASTER_DATA.get_indian_states_and_union_territories()
    categories = MASTER_DATA.get_product_categories()

    with st.form(f"{prefix}_manufacturer_profile_form"):
        col1, col2 = st.columns(2)
        business_name = col1.text_input("Business / Manufacturer Name", value=defaults.get("business_name", defaults.get("manufacturer_name", "")))
        brand_name = col2.text_input("Brand Name", value=defaults.get("brand_name", ""))
        owner_name = col1.text_input("Owner Name", value=defaults.get("owner_name", ""))
        contact_person = col2.text_input("Contact Person", value=defaults.get("contact_person", defaults.get("owner_name", "")))
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

        business_description = st.text_area("Business Description", value=defaults.get("business_description", ""), height=120)
        st.caption("Optional uploads like GST certificate, PAN image, Aadhaar image, shop photo, and cancelled cheque are not implemented yet.")
        submitted = st.form_submit_button(submit_label)

    payload = {
        "business_name": business_name.strip(),
        "manufacturer_name": business_name.strip(),
        "brand_name": brand_name.strip(),
        "owner_name": owner_name.strip(),
        "contact_person": contact_person.strip(),
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
    }
    return submitted, payload


def render_manufacturer_onboarding(app_context: dict) -> None:
    current_user = app_context["current_user"]
    onboarding_service = app_context["manufacturer_onboarding_service"]
    governance_service = app_context["governance_service"]

    if not current_user:
        render_page_header("Onboarding", "Use Google sign-in first to open the correct onboarding workspace.", ["Access Required"])
        st.info("Sign in to access onboarding.")
        return

    if current_user.role in {"manufacturer", "admin_as_manufacturer"}:
        manufacturer = governance_service.get_manufacturer(current_user.manufacturer_code or "")
        render_page_header("Onboarding", "Complete and maintain your manufacturer business profile from this dedicated route only.", ["Manufacturer", "Onboarding"])
        render_metric_grid(
            [
                render_metric_card("Status", (manufacturer or {}).get("status", "ACTIVE"), "SUCCESS"),
                render_metric_card("Workspace", current_user.manufacturer_code or "Not mapped", "OPEN"),
            ]
        )
        render_section_intro("Manufacturer Profile", "Dashboard no longer contains onboarding forms. This route is where invited manufacturers can complete profile details before admin activation.")
        if not manufacturer:
            st.info("No manufacturer registry record is linked to this account yet.")
            return

        st.markdown(
            render_mobile_record_card(
                {
                    "Business": manufacturer.get("business_name", manufacturer.get("manufacturer_name", "")),
                    "Owner": manufacturer.get("owner_name", ""),
                    "City": _address_of(manufacturer).get("city", ""),
                    "Status": manufacturer.get("status", "ACTIVE"),
                }
            ),
            unsafe_allow_html=True,
        )
        submitted, payload = _render_profile_form(
            prefix="manufacturer_self",
            defaults=manufacturer,
            submit_label="Save Manufacturer Profile",
        )
        if submitted:
            onboarding_service.update_manufacturer(current_user.manufacturer_code or "", payload)
            st.success("Manufacturer profile saved. Admin approval may still be required before full activation.")
            st.rerun()
        return

    if current_user.role not in {"admin", "platform_admin"}:
        render_page_header("Onboarding", "Platform-admin only onboarding for new manufacturers and their first-time secrets.", ["Admin Only"])
        st.info("Only platform admin can access manufacturer onboarding.")
        return

    manufacturers = governance_service.list_manufacturers()
    render_page_header("Onboarding", "Create and manage manufacturer onboarding profiles with complete business details and first-time setup secrets.", ["Platform Admin", "Onboarding"])
    render_metric_grid(
        [
            render_metric_card("Manufacturers", str(len(manufacturers)), "SUCCESS"),
            render_metric_card("Active Manufacturers", str(len([item for item in manufacturers if item.get("status") == "ACTIVE"])), "SUCCESS"),
        ]
    )
    render_section_intro("First-Time Setup", "New manufacturer profiles now follow invite -> profile completion -> admin approval before full ACTIVE access.")

    next_code = onboarding_service.generate_next_manufacturer_code()
    with st.form("manufacturer_onboarding_create_code"):
        code_col, plan_col = st.columns(2)
        code_col.text_input("Manufacturer Code", value=next_code, disabled=True)
        subscription_plan = plan_col.selectbox("Subscription Plan", SUBSCRIPTION_PLANS, index=0)
        create_code_submit = st.form_submit_button("Open Manufacturer Create Form")

    if create_code_submit:
        st.session_state[PENDING_CREATE_CODE_KEY] = next_code

    pending_create_code = st.session_state.get(PENDING_CREATE_CODE_KEY, "")
    if pending_create_code:
        st.markdown(f"### New Manufacturer Profile: `{pending_create_code}`")
        create_submitted, create_payload = _render_profile_form(
            prefix="admin_create",
            defaults={},
            submit_label="Create Manufacturer Onboarding",
        )
        if create_submitted:
            created = onboarding_service.create_manufacturer(
                manufacturer_code=pending_create_code,
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
                created_by=current_user.email,
                subscription_plan=subscription_plan,
            )
            st.session_state.pop(PENDING_CREATE_CODE_KEY, None)
            st.success(f"Manufacturer {created['manufacturer_code']} created.")
            st.code(created["manufacturer_onboarding_steps"], language="text")
            st.rerun()

    st.markdown("### Registered Manufacturers")
    st.dataframe(manufacturers, use_container_width=True)

    if not manufacturers:
        return

    selected_code = st.selectbox("Manage Manufacturer", [item["manufacturer_code"] for item in manufacturers])
    selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)

    with st.form("manufacturer_onboarding_update"):
        col1, col2 = st.columns(2)
        updated_name = col1.text_input("Update Name", value=selected.get("business_name", selected.get("manufacturer_name", "")))
        updated_email = col2.text_input("Update Owner Email", value=selected.get("owner_email", ""))
        updated_city = col1.text_input("Update City", value=_address_of(selected).get("city", ""))
        updated_status = col2.selectbox("Update Status", ["ACTIVE", "INACTIVE", "BLOCKED"], index=_option_index(["ACTIVE", "INACTIVE", "BLOCKED"], selected.get("status", "ACTIVE")))
        updated_plan = st.selectbox("Subscription Plan", SUBSCRIPTION_PLANS, index=_subscription_plan_index(selected.get("subscription_plan", "basic")))
        save_submit = st.form_submit_button("Save Changes")

    if save_submit:
        onboarding_service.update_manufacturer(
            selected_code,
            {
                "manufacturer_name": updated_name.strip(),
                "business_name": updated_name.strip(),
                "owner_email": updated_email.strip(),
                "city": updated_city.strip(),
                "address": {"city": updated_city.strip()},
                "status": updated_status.strip(),
                "subscription_plan": updated_plan.strip(),
            },
        )
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

    st.markdown("### Shareable Onboarding Packet")
    st.code(selected.get("manufacturer_onboarding_steps", ""), language="text")
