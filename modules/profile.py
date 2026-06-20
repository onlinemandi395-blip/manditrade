from __future__ import annotations

import streamlit as st

from services.auth_service import normalize_role
from services.user_profile_service import UserProfileService


REQUIRED_MERCHANT_FIELDS = ("business_name", "upi_id", "gst_number", "invoice_name")
BUSINESS_ROLES = {"merchant", "platform_admin"}


def merchant_profile_completion_status(profile: dict) -> tuple[bool, list[str]]:
    details = dict((profile or {}).get("details", {}) or {})
    missing = [field for field in REQUIRED_MERCHANT_FIELDS if not str(details.get(field, "")).strip()]
    return (not missing, missing)


def _save_contact_profile(
    *,
    profile_service: UserProfileService,
    profile: dict,
    email: str,
    role: str,
    contact_name: str,
    mobile: str,
    details_updates: dict | None = None,
) -> dict:
    next_profile = dict(profile)
    existing_details = dict(profile.get("details", {}) or {})
    existing_details.update(dict(details_updates or {}))
    existing_details["profile_completed"] = True
    next_profile["display_name"] = contact_name.strip()
    next_profile["mobile"] = mobile.strip()
    next_profile["details"] = existing_details
    return profile_service.save_profile(
        actor_email=email,
        actor_role=role,
        target_email=email,
        updates=next_profile,
    )


def _sync_owned_products_for_merchant(data_service, *, email: str, details: dict, is_complete: bool) -> None:
    products = data_service.get_collection_ref("products")
    products_changed = False
    for product in products:
        if str(((product.get("owner") or {}).get("email", ""))).strip().lower() != email:
            continue
        product["posting_status"] = "READY_TO_POST" if is_complete else "DUE_FOR_POSTING"
        product["owner_business_details"] = dict(details)
        products_changed = True
    if products_changed:
        data_service.persist_collection("products")


def render_profile_page(data_service, session_service) -> None:
    user = session_service.get_user()
    email = str(user.get("email", "")).strip().lower()
    role = normalize_role(str(user.get("role", "")).strip().lower())
    profile_service = UserProfileService(data_service)
    profile = profile_service.get_or_create_profile(
        email=email,
        role=role or "public_buyer",
        display_name=str(user.get("display_name", "")).strip(),
        mobile="",
    )
    details = dict(profile.get("details", {}) or {})

    st.markdown("### My Profile")
    with st.container(border=True):
        st.caption("Contact")
        contact_cols = st.columns(2, gap="small")
        contact_name = contact_cols[0].text_input("Full Name", value=str(profile.get("display_name", "") or ""), key="profile_full_name")
        mobile = contact_cols[1].text_input("Mobile Number", value=str(profile.get("mobile", "") or ""), key="profile_mobile")
        st.text_input("Email", value=email, disabled=True, key="profile_email")
    if role in {"public_buyer", "merchant_buyer"}:
        with st.container(border=True):
            st.caption("Buying Details")
            st.write("Keep this simple. Address can be managed during checkout.")
        optional_gst = ""
        if role == "public_buyer":
            with st.container(border=True):
                optional_gst = st.text_input(
                    "GST Number (Optional)",
                    value=str(details.get("gst_number", "") or ""),
                    key="profile_public_optional_gst",
                )
        if st.button("Save Profile", use_container_width=True, key="save_profile_contact_only"):
            _save_contact_profile(
                profile_service=profile_service,
                profile=profile,
                email=email,
                role=role,
                contact_name=contact_name,
                mobile=mobile,
                details_updates={"gst_number": optional_gst.strip()} if role == "public_buyer" else {},
            )
            st.success("Profile saved.")
            st.rerun()
        return

    with st.container(border=True):
        st.caption("Business")
        row_one = st.columns(2, gap="small")
        business_name = row_one[0].text_input("Business Name", value=str(details.get("business_name", "") or ""), key="profile_business_name")
        upi_id = row_one[1].text_input("UPI ID", value=str(details.get("upi_id", "") or ""), key="profile_upi_id")
        row_two = st.columns(2, gap="small")
        gst_number = row_two[0].text_input("GST Number", value=str(details.get("gst_number", "") or ""), key="profile_gst_number")
        invoice_name = row_two[1].text_input("Invoice Name", value=str(details.get("invoice_name", "") or ""), key="profile_invoice_name")

    with st.container(border=True):
        st.caption("Billing")
        invoice_address = st.text_area("Invoice Address", value=str(details.get("invoice_address", "") or ""), height=90, key="profile_invoice_address")
        billing_cols = st.columns(3, gap="small")
        invoice_phone = billing_cols[0].text_input("Invoice Contact Phone", value=str(details.get("invoice_phone", "") or ""), key="profile_invoice_phone")
        bank_account_name = billing_cols[1].text_input("Bank Account Name", value=str(details.get("bank_account_name", "") or ""), key="profile_bank_account_name")
        bank_account_number = billing_cols[2].text_input("Bank Account Number", value=str(details.get("bank_account_number", "") or ""), key="profile_bank_account_number")
        bank_ifsc = st.text_input("Bank IFSC", value=str(details.get("bank_ifsc", "") or ""), key="profile_bank_ifsc")
        other_details = st.text_area("Other Notes", value=str(details.get("other_details", "") or ""), key="profile_other_details")

    preview_profile = {
        "details": {
            "business_name": business_name,
            "upi_id": upi_id,
            "gst_number": gst_number,
            "invoice_name": invoice_name,
        }
    }
    is_complete, missing = merchant_profile_completion_status(preview_profile)
    with st.container(border=True):
        st.caption("Status")
        if is_complete:
            st.success("Business profile is complete.")
        else:
            st.warning(f"Missing: {', '.join(missing)}")

    if st.button("Save Profile", use_container_width=True, key="save_profile_business"):
        next_details = {
            **details,
            "business_name": business_name.strip(),
            "upi_id": upi_id.strip(),
            "gst_number": gst_number.strip(),
            "invoice_name": invoice_name.strip(),
            "invoice_address": invoice_address.strip(),
            "invoice_phone": invoice_phone.strip(),
            "bank_account_name": bank_account_name.strip(),
            "bank_account_number": bank_account_number.strip(),
            "bank_ifsc": bank_ifsc.strip(),
            "other_details": other_details.strip(),
            "profile_completed": is_complete,
        }
        profile_service.save_profile(
            actor_email=email,
            actor_role=role,
            target_email=email,
            updates={
                **profile,
                "display_name": contact_name.strip(),
                "mobile": mobile.strip(),
                "details": next_details,
            },
        )
        if role == "merchant":
            _sync_owned_products_for_merchant(
                data_service,
                email=email,
                details=next_details,
                is_complete=is_complete,
            )
        st.success("Profile saved.")
        st.rerun()
