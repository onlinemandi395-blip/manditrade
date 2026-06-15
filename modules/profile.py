from __future__ import annotations

import streamlit as st

from services.user_profile_service import UserProfileService


REQUIRED_OWNER_FIELDS = ("business_name", "upi_id", "gst_number")


def owner_profile_completion_status(profile: dict) -> tuple[bool, list[str]]:
    details = dict((profile or {}).get("details", {}) or {})
    missing = [field for field in REQUIRED_OWNER_FIELDS if not str(details.get(field, "")).strip()]
    return (not missing, missing)


def render_profile_page(data_service, session_service) -> None:
    user = session_service.get_user()
    email = str(user.get("email", "")).strip().lower()
    role = str(user.get("role", "")).strip().lower()
    profile_service = UserProfileService(data_service)
    profile = profile_service.get_or_create_profile(
        email=email,
        role=role or "public_buyer",
        display_name=str(user.get("display_name", "")).strip(),
        mobile="",
    )
    details = dict(profile.get("details", {}) or {})

    business_name = st.text_input("Business Name", value=str(details.get("business_name", "") or ""))
    upi_id = st.text_input("UPI ID", value=str(details.get("upi_id", "") or ""))
    gst_number = st.text_input("GST Number", value=str(details.get("gst_number", "") or ""))
    contact_name = st.text_input("Contact Name", value=str(profile.get("display_name", "") or ""))
    mobile = st.text_input("Mobile", value=str(profile.get("mobile", "") or ""))
    other_details = st.text_area("Other Required Details", value=str(details.get("other_details", "") or ""))

    preview_profile = {"details": {"business_name": business_name, "upi_id": upi_id, "gst_number": gst_number}}
    is_complete, missing = owner_profile_completion_status(preview_profile)
    if is_complete:
        st.success("Profile is complete.")
    else:
        st.warning(f"Profile incomplete. Missing: {', '.join(missing)}")

    if st.button("Save Profile", use_container_width=True):
        next_profile = dict(profile)
        next_profile["display_name"] = contact_name.strip()
        next_profile["mobile"] = mobile.strip()
        next_profile["details"] = {
            **details,
            "business_name": business_name.strip(),
            "upi_id": upi_id.strip(),
            "gst_number": gst_number.strip(),
            "other_details": other_details.strip(),
            "profile_completed": is_complete,
        }
        profile_service.save_profile(
            actor_email=email,
            actor_role=role,
            target_email=email,
            updates=next_profile,
        )
        products = data_service.get_collection_ref("products")
        products_changed = False
        for product in products:
            if str(((product.get("owner") or {}).get("email", ""))).strip().lower() != email:
                continue
            product["posting_status"] = "READY_TO_POST" if is_complete else "DUE_FOR_POSTING"
            product["owner_business_details"] = {
                "business_name": business_name.strip(),
                "upi_id": upi_id.strip(),
                "gst_number": gst_number.strip(),
                "other_details": other_details.strip(),
                "profile_completed": is_complete,
            }
            products_changed = True
        if products_changed:
            data_service.persist_collection("products")
        st.success("Profile saved.")
        st.rerun()
