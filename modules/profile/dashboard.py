from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header
from modules.onboarding.manufacturer_onboarding import _address_of as manufacturer_address_of
from modules.onboarding.manufacturer_onboarding import _render_profile_form as render_manufacturer_profile_form

WORK_TYPES = [
    "Full-time",
    "Part-time",
    "Daily Wage",
    "Shift-based",
    "Loading/unloading",
    "Packaging",
    "Machine operator",
    "Driver/helper",
    "Emergency labour",
]


def _address_value(address: dict | None) -> dict:
    address = address or {}
    return {
        "line1": address.get("line1", ""),
        "line2": address.get("line2", ""),
        "city": address.get("city", ""),
        "state": address.get("state", ""),
        "pin_code": address.get("pin_code", ""),
        "landmark": address.get("landmark", ""),
    }


def _admin_profile_defaults(current_user, stored: dict | None) -> dict:
    stored = stored or {}
    return {
        "full_name": stored.get("full_name") or getattr(current_user, "name", "") or "",
        "email": stored.get("email") or getattr(current_user, "email", "") or "",
        "mobile": stored.get("mobile", ""),
        "alternate_mobile": stored.get("alternate_mobile", ""),
        "designation": stored.get("designation", "Platform Admin"),
        "office_name": stored.get("office_name", "MandiTrade Control Center"),
        "address": _address_value(stored.get("address", {})),
        "support_email": stored.get("support_email", getattr(current_user, "email", "") or ""),
        "notification_email": stored.get("notification_email", getattr(current_user, "email", "") or ""),
        "credential_reference": stored.get("credential_reference", ""),
        "credential_notes": stored.get("credential_notes", ""),
        "profile_notes": stored.get("profile_notes", ""),
    }


def _render_admin_profile_form(current_user, stored: dict | None) -> tuple[bool, dict]:
    defaults = _admin_profile_defaults(current_user, stored)
    address = defaults["address"]
    with st.form("admin_profile_form"):
        col1, col2 = st.columns(2)
        full_name = col1.text_input("Full Name", value=defaults["full_name"])
        admin_email = col2.text_input("Admin Email", value=defaults["email"], disabled=True)
        mobile = col1.text_input("Mobile Number", value=defaults["mobile"])
        alternate_mobile = col2.text_input("Alternate Mobile Number", value=defaults["alternate_mobile"])
        office_name = col1.text_input("Office Name", value=defaults["office_name"])
        designation = col2.text_input("Designation", value=defaults["designation"])

        st.markdown("#### Address")
        line1 = st.text_input("Full Address", value=address["line1"])
        line2 = st.text_input("Address Line 2", value=address["line2"])
        city_col, state_col, pin_col = st.columns(3)
        city = city_col.text_input("City", value=address["city"])
        state = state_col.text_input("State", value=address["state"])
        pin_code = pin_col.text_input("PIN Code", value=address["pin_code"])

        st.markdown("#### Operations")
        support_email = col1.text_input("Support Email", value=defaults["support_email"])
        notification_email = col2.text_input("Notification Email", value=defaults["notification_email"])
        credential_reference = st.text_input("Credential Reference", value=defaults["credential_reference"], help="Store only human-readable references, not passwords or OAuth secrets.")
        credential_notes = st.text_area("Credential Notes", value=defaults["credential_notes"], height=100)
        profile_notes = st.text_area("Profile Notes", value=defaults["profile_notes"], height=120)
        submitted = st.form_submit_button("Save Admin Profile")

    return submitted, {
        "email": defaults["email"],
        "full_name": full_name.strip(),
        "mobile": mobile.strip(),
        "alternate_mobile": alternate_mobile.strip(),
        "office_name": office_name.strip(),
        "designation": designation.strip(),
        "address": {
            "line1": line1.strip(),
            "line2": line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
        },
        "support_email": support_email.strip(),
        "notification_email": notification_email.strip(),
        "credential_reference": credential_reference.strip(),
        "credential_notes": credential_notes.strip(),
        "profile_notes": profile_notes.strip(),
    }


def _render_client_profile_form(current_user, profile: dict) -> tuple[bool, dict]:
    address = _address_value(profile.get("address", {}))
    delivery_contact = profile.get("delivery_contact", {}) or {}
    with st.form("client_profile_form"):
        col1, col2 = st.columns(2)
        business_name = col1.text_input("Business Name", value=profile.get("business_name", ""))
        owner_name = col2.text_input("Owner Name", value=profile.get("owner_name", ""))
        email_value = col1.text_input("Email", value=current_user.email, disabled=True)
        mobile = col2.text_input("Mobile Number", value=profile.get("mobile", ""))
        alternate_mobile = col1.text_input("Alternate Mobile Number", value=profile.get("alternate_mobile", ""))
        gstin = col2.text_input("GSTIN", value=profile.get("gstin", ""))

        st.markdown("#### Delivery Address")
        line1 = st.text_input("Full Address", value=address["line1"])
        line2 = st.text_input("Address Line 2", value=address["line2"])
        city_col, state_col, pin_col = st.columns(3)
        city = city_col.text_input("City", value=address["city"])
        state = state_col.text_input("State", value=address["state"])
        pin_code = pin_col.text_input("PIN Code", value=address["pin_code"])
        landmark = st.text_input("Landmark", value=address["landmark"])

        st.markdown("#### Delivery Preferences")
        contact_col1, contact_col2 = st.columns(2)
        delivery_contact_name = contact_col1.text_input("Delivery Contact Name", value=delivery_contact.get("name", owner_name))
        delivery_contact_number = contact_col2.text_input("Delivery Contact Number", value=delivery_contact.get("mobile", mobile))
        delivery_instructions = st.text_area("Delivery Instructions", value=profile.get("delivery_instructions", ""), height=110)
        submitted = st.form_submit_button("Save Client Profile")

    return submitted, {
        "business_name": business_name.strip(),
        "owner_name": owner_name.strip(),
        "email": email_value.strip().lower(),
        "mobile": mobile.strip(),
        "alternate_mobile": alternate_mobile.strip(),
        "gstin": gstin.strip(),
        "address": {
            "line1": line1.strip(),
            "line2": line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
            "landmark": landmark.strip(),
        },
        "delivery_contact": {
            "name": delivery_contact_name.strip(),
            "mobile": delivery_contact_number.strip(),
        },
        "delivery_instructions": delivery_instructions.strip(),
    }


def _render_worker_profile_form(current_user, worker: dict | None) -> tuple[bool, dict]:
    worker = worker or {}
    selected_types = [item for item in worker.get("preferred_work_type", []) if item in WORK_TYPES]
    skills_text = ", ".join(worker.get("skills", []) or [])
    with st.form("worker_profile_form"):
        col1, col2 = st.columns(2)
        name = col1.text_input("Name", value=worker.get("name", getattr(current_user, "name", "") or ""))
        email_value = col2.text_input("Linked Email", value=current_user.email, disabled=True)
        mobile = col1.text_input("Mobile Number", value=worker.get("mobile", ""))
        city = col2.text_input("City", value=worker.get("city", ""))
        area = col1.text_input("Area", value=worker.get("area", ""))
        available = col2.checkbox("Available for Work", value=worker.get("available", True))
        public_profile_opt_in = st.checkbox("Allow manufacturers to see public worker profile", value=worker.get("public_profile_opt_in", True))
        skills = st.text_input("Skills", value=skills_text, help="Comma-separated skills like Loading, Packaging, Driver.")
        preferred_work_type = st.multiselect("Preferred Work Type", WORK_TYPES, default=selected_types)
        submitted = st.form_submit_button("Save Worker Profile")

    return submitted, {
        "linked_email": email_value.strip().lower(),
        "name": name.strip(),
        "mobile": mobile.strip(),
        "city": city.strip(),
        "area": area.strip(),
        "skills": [item.strip() for item in skills.split(",") if item.strip()],
        "preferred_work_type": preferred_work_type,
        "available": available,
        "public_profile_opt_in": public_profile_opt_in,
    }


def _render_admin_profile(app_context: dict) -> None:
    current_user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    security_service = app_context["security_service"]
    stored = governance_service.get_admin_profile(current_user.email)
    render_page_header("My Profile", "Maintain your platform-admin contact details and operational profile from one safe place.", ["Platform Admin", "Profile"])
    render_metric_grid(
        [
            render_metric_card("Role", "Platform Admin", "SUCCESS"),
            render_metric_card("Email", current_user.email, "OPEN"),
        ]
    )
    render_section_intro("Admin Identity", "Sensitive OAuth and runtime secrets stay in Streamlit secrets. This page stores only profile and operational contact details.")
    if stored:
        render_3d_panel(
            render_mobile_record_card(
                {
                    "Full Name": stored.get("full_name", ""),
                    "Designation": stored.get("designation", ""),
                    "Support Email": stored.get("support_email", ""),
                }
            ),
            "Saved Admin Profile",
        )
    render_section_intro("Admin Runtime Access", "If runtime unlock is needed, use it here instead of the sidebar.")
    vault_ready = security_service.admin_vault_matches_user(current_user)
    expander_title = "Admin Runtime Vault" if vault_ready else "Unlock Admin Drive Runtime"
    with st.expander(expander_title, expanded=False):
        if vault_ready:
            st.success("Vault-backed admin runtime unlock is available for this account.")
            verification_key = ""
            button_label = "Unlock From Vault"
        else:
            verification_key = st.text_input("Verification Key", type="password", key="admin_profile_runtime_key")
            button_label = "Verify And Unlock"
        if st.button(button_label, use_container_width=True, key="admin_profile_runtime_unlock"):
            try:
                runtime_state = security_service.unlock_admin_runtime(current_user, verification_key)
                st.success(f"Admin runtime unlocked for {runtime_state['principal']}.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
    submitted, payload = _render_admin_profile_form(current_user, stored)
    if submitted:
        governance_service.upsert_admin_profile(payload)
        st.success("Admin profile saved.")
        st.rerun()


def _render_manufacturer_profile(app_context: dict) -> None:
    current_user = app_context["current_user"]
    manufacturer = app_context["governance_service"].get_manufacturer(current_user.manufacturer_code or "")
    render_page_header("My Profile", "Maintain business, legal, banking, and workspace identity details from one dedicated profile page.", ["Manufacturer", "Profile"])
    if not manufacturer:
        st.info("No manufacturer registry record is linked to this account yet.")
        return
    render_metric_grid(
        [
            render_metric_card("Workspace", current_user.manufacturer_code or "Not mapped", "OPEN"),
            render_metric_card("Status", manufacturer.get("status", "ACTIVE"), "SUCCESS"),
            render_metric_card("Drive", manufacturer.get("google_drive_connected_status", "NOT_CONNECTED"), "PENDING"),
        ]
    )
    render_section_intro("Business Profile", "Use this page to keep manufacturer business, legal, and banking details current.")
    render_3d_panel(
        render_mobile_record_card(
            {
                "Business": manufacturer.get("business_name", manufacturer.get("manufacturer_name", "")),
                "Owner": manufacturer.get("owner_name", ""),
                "City": manufacturer_address_of(manufacturer).get("city", ""),
                "Plan": manufacturer.get("subscription_plan", "Basic"),
            }
        ),
        "Current Manufacturer Profile",
    )
    submitted, payload = render_manufacturer_profile_form(
        prefix="my_profile_manufacturer",
        defaults=manufacturer,
        submit_label="Save Manufacturer Profile",
    )
    if submitted:
        app_context["manufacturer_onboarding_service"].update_manufacturer(current_user.manufacturer_code or "", payload)
        st.success("Manufacturer profile saved.")
        st.rerun()


def _render_client_profile(app_context: dict) -> None:
    current_user = app_context["current_user"]
    client_service = app_context["client_service"]
    profile = client_service.get_client_profile_by_email(current_user.manufacturer_code or "", current_user.email)
    render_page_header("My Profile", "Keep client business and delivery details updated so orders reach the right place smoothly.", ["Client", "Delivery Profile"])
    if not current_user.manufacturer_code:
        st.info("Your client account is not mapped to a manufacturer workspace yet.")
        return
    if not profile:
        st.info("No active client profile is linked to this email yet.")
        return
    render_metric_grid(
        [
            render_metric_card("Manufacturer", current_user.manufacturer_code, "OPEN"),
            render_metric_card("Status", profile.get("status", "ACTIVE"), "SUCCESS"),
            render_metric_card("Delivery City", _address_value(profile.get("address", {})).get("city", "Not set"), "PENDING"),
        ]
    )
    render_section_intro("Client Delivery Profile", "Update billing, mobile, and delivery preferences here for smoother fulfilment.")
    render_3d_panel(
        render_mobile_record_card(
            {
                "Business": profile.get("business_name", ""),
                "Owner": profile.get("owner_name", ""),
                "Email": profile.get("email", ""),
                "City": _address_value(profile.get("address", {})).get("city", ""),
            }
        ),
        "Current Client Profile",
    )
    submitted, payload = _render_client_profile_form(current_user, profile)
    if submitted:
        client_service.upsert_client_profile(current_user.manufacturer_code or "", current_user.email, payload)
        st.success("Client profile saved.")
        st.rerun()


def _render_worker_profile(app_context: dict) -> None:
    current_user = app_context["current_user"]
    worker_service = app_context["worker_service"]
    worker = worker_service.get_worker_by_email(current_user.email)
    render_page_header("My Profile", "Maintain your worker identity, location, and skill details so mandi jobs reach you faster.", ["Worker", "Profile"])
    render_metric_grid(
        [
            render_metric_card("Status", (worker or {}).get("status", "ACTIVE"), "SUCCESS"),
            render_metric_card("Availability", "Available" if (worker or {}).get("available", True) else "Busy", "OPEN"),
            render_metric_card("Public Profile", "Enabled" if (worker or {}).get("public_profile_opt_in", True) else "Hidden", "PENDING"),
        ]
    )
    render_section_intro("Worker Details", "Keep your city, area, skills, and work preferences updated for better local job matching.")
    if worker:
        render_3d_panel(
            render_mobile_record_card(
                {
                    "Name": worker.get("name", ""),
                    "City": worker.get("city", ""),
                    "Area": worker.get("area", ""),
                    "Skills": ", ".join(worker.get("skills", [])[:3]),
                }
            ),
            "Current Worker Profile",
        )
    submitted, payload = _render_worker_profile_form(current_user, worker)
    if submitted:
        worker_service.upsert_worker(**payload)
        st.success("Worker profile saved.")
        st.rerun()


def _render_public_buyer_profile_form(current_user, profile: dict) -> tuple[bool, dict]:
    address = _address_value(profile.get("address", {}))
    with st.form("public_buyer_profile_form"):
        col1, col2 = st.columns(2)
        full_name = col1.text_input("Full Name", value=profile.get("full_name", getattr(current_user, "name", "") or ""))
        email_value = col2.text_input("Email", value=current_user.email, disabled=True)
        mobile = col1.text_input("Mobile Number", value=profile.get("mobile", ""))
        alternate_mobile = col2.text_input("Alternate Mobile Number", value=profile.get("alternate_mobile", ""))
        st.markdown("#### Delivery Address")
        line1 = st.text_input("Address Line 1", value=address["line1"])
        line2 = st.text_input("Address Line 2", value=address["line2"])
        city_col, state_col, pin_col = st.columns(3)
        city = city_col.text_input("City", value=address["city"])
        state = state_col.text_input("State", value=address["state"])
        pin_code = pin_col.text_input("PIN Code", value=address["pin_code"])
        landmark = st.text_input("Landmark", value=address["landmark"])
        delivery_instructions = st.text_area("Delivery Instructions", value=profile.get("delivery_instructions", ""), height=110)
        submitted = st.form_submit_button("Save Public Buyer Profile")
    return submitted, {
        "email": email_value.strip().lower(),
        "full_name": full_name.strip(),
        "mobile": mobile.strip(),
        "alternate_mobile": alternate_mobile.strip(),
        "address": {
            "line1": line1.strip(),
            "line2": line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
            "landmark": landmark.strip(),
        },
        "delivery_instructions": delivery_instructions.strip(),
    }


def _render_public_buyer_profile(app_context: dict) -> None:
    current_user = app_context["current_user"]
    service = app_context["public_buyer_service"]
    profile = service.get_by_email(current_user.email)
    render_page_header("My Profile", "Maintain public-buyer delivery details so instant-pay marketplace orders reach the correct address smoothly.", ["Public Buyer", "Delivery Profile"])
    if not profile:
        st.info("No public buyer profile is linked to this account yet.")
        return
    render_metric_grid(
        [
            render_metric_card("Role", "Public Buyer", "SUCCESS"),
            render_metric_card("Status", profile.get("status", "ACTIVE"), "OPEN"),
            render_metric_card("Delivery City", _address_value(profile.get("address", {})).get("city", "Not set"), "PENDING"),
        ]
    )
    render_section_intro("Public Delivery Profile", "This profile is used only for public marketplace shopping. It does not unlock ledger, RFQ, or private-client flows.")
    render_3d_panel(
        render_mobile_record_card(
            {
                "Name": profile.get("full_name", ""),
                "Email": profile.get("email", ""),
                "City": _address_value(profile.get("address", {})).get("city", ""),
                "Mobile": profile.get("mobile", ""),
            }
        ),
        "Current Public Buyer Profile",
    )
    submitted, payload = _render_public_buyer_profile_form(current_user, profile)
    if submitted:
        service.upsert_profile(profile["public_buyer_id"], payload)
        st.success("Public buyer profile saved.")
        st.rerun()


def render_my_profile_dashboard(app_context: dict) -> None:
    current_user = app_context["current_user"]
    if not current_user:
        render_page_header("My Profile", "Sign in first to manage your account and profile details.", ["Access Required"])
        st.info("Use Google sign-in to open your profile workspace.")
        return
    if current_user.role in {"admin", "platform_admin"}:
        _render_admin_profile(app_context)
        return
    if current_user.role in {"manufacturer", "admin_as_manufacturer"}:
        _render_manufacturer_profile(app_context)
        return
    if current_user.role == "client":
        _render_client_profile(app_context)
        return
    if current_user.role == "worker":
        _render_worker_profile(app_context)
        return
    if current_user.role == "public_buyer":
        _render_public_buyer_profile(app_context)
        return
    render_page_header("My Profile", "This account type does not have a dedicated profile form yet.", ["Profile"])
    st.info("No editable profile is available for this role right now.")
