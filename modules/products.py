from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from datetime import UTC, datetime

import streamlit as st

from components.html_renderer import render_template
from components.product_grid import render_product_grid
from components.table_renderer import render_table
from services.auth_service import is_bootstrap_admin
from services.id_service import IdService
from services.media_service import MediaService
from services.product_consent_service import ProductConsentService
from services.user_profile_service import UserProfileService


OWNER_TYPES = {"Merchant": "merchant"}
STATUSES = ["PENDING_APPROVAL", "APPROVED", "REJECTED", "ARCHIVED"]
MASTER_CATEGORY_ROWS = [
    {"category": "Textile", "subcategories": ["Towel", "Bedsheet", "Curtain", "Blanket", "Fabric Roll", "Uniform", "Pillow Cover", "Mattress Cover", "Bath Linen", "Home Furnishing"]},
    {"category": "Raw Material", "subcategories": ["Cotton", "Thread", "Yarn", "Packaging", "Dye", "Chemical", "Polyester", "Foam", "Elastic", "Buttons"]},
    {"category": "Food Grain", "subcategories": ["Rice", "Wheat", "Pulses", "Maize", "Millet", "Flour", "Sugar", "Salt", "Spices", "Oil Seeds"]},
    {"category": "Industrial", "subcategories": ["Steel", "Machine Parts", "Tools", "Motor", "Pump", "Rack", "Bearings", "Fasteners", "Belts", "Industrial Consumables"]},
    {"category": "Electronics", "subcategories": ["Mobile Accessories", "Wiring", "Switches", "LED", "Battery", "Charger", "Adapters", "Cables", "Inverter", "Control Panel"]},
    {"category": "Packaging", "subcategories": ["Box", "Carton", "Bag", "Tape", "Label", "Bubble Wrap", "Pouch", "Shrink Film", "Containers", "Straps"]},
    {"category": "Agriculture", "subcategories": ["Seeds", "Fertilizer", "Tools", "Irrigation", "Animal Feed", "Pesticide", "Farm Equipment", "Saplings", "Organic Inputs", "Mulch"]},
    {"category": "Construction", "subcategories": ["Cement", "Sand", "Bricks", "Tiles", "Paint", "Hardware", "Pipes", "Steel Rod", "Electrical Fittings", "Stone"]},
    {"category": "Furniture", "subcategories": ["Chair", "Table", "Rack", "Door", "Bed", "Cabinet", "Sofa", "Workstation", "Storage Unit", "Wood Panel"]},
    {"category": "Apparel", "subcategories": ["T-Shirt", "Shirt", "Uniform", "Jacket", "Kids Wear", "Women's Wear", "Innerwear", "Sportswear", "Denim", "Ethnic Wear"]},
    {"category": "Home Utility", "subcategories": ["Cleaning Supplies", "Kitchenware", "Plastic Items", "Buckets", "Storage Boxes", "Bathroom Items", "Mats", "Laundry Items"]},
    {"category": "Healthcare", "subcategories": ["Masks", "Gloves", "Disposables", "Medical Equipment", "Sanitizer", "Supplements", "Bandages", "Diagnostics"]},
    {"category": "Automotive", "subcategories": ["Lubricants", "Filters", "Tyres", "Spare Parts", "Batteries", "Cleaning Kits", "Seat Covers", "Tools"]},
    {"category": "Office Supplies", "subcategories": ["Paper", "Registers", "Pens", "Printer Consumables", "Files", "Stationery Sets", "Office Furniture"]},
    {"category": "Other", "subcategories": ["General"]},
]


def _build_user_index(users: list[dict]) -> dict[str, dict]:
    return {str(user.get("email", "")).strip().lower(): user for user in users if str(user.get("email", "")).strip()}


def _active_users_for_role(users: list[dict], role: str) -> list[dict]:
    normalized_role = str(role).strip().lower()
    accepted_roles = {normalized_role}
    if normalized_role == "worker":
        accepted_roles.add("delivery_partner")
    rows = [
        user for user in users
        if str(user.get("role", "")).strip().lower() in accepted_roles
        and str(user.get("status", "ACTIVE")).strip().upper() == "ACTIVE"
        and str(user.get("email", "")).strip()
    ]
    return sorted(rows, key=lambda user: (str(user.get("display_name", "")).strip().lower(), str(user.get("email", "")).strip().lower()))


def _owner_candidates_for_role(users: list[dict], products: list[dict], role: str) -> list[dict]:
    normalized_role = str(role).strip().lower()
    candidate_map: dict[str, dict] = {
        str(user.get("email", "")).strip().lower(): dict(user)
        for user in _active_users_for_role(users, normalized_role)
    }
    for product in products:
        owner = dict(product.get("owner", {}) or {})
        owner_email = str(owner.get("email", "")).strip().lower()
        owner_role = str(owner.get("role", "")).strip().lower()
        if not owner_email or owner_role != normalized_role:
            continue
        if owner_email not in candidate_map:
            candidate_map[owner_email] = {
                "user_id": str(owner.get("user_id", "")).strip(),
                "email": owner_email,
                "role": normalized_role,
                "status": "ACTIVE",
                "display_name": str(owner.get("display_name", "")).strip(),
                "phone": str(owner.get("phone", "")).strip(),
                "source": "product_owner_fallback",
            }
    return sorted(
        candidate_map.values(),
        key=lambda user: (str(user.get("display_name", "")).strip().lower(), str(user.get("email", "")).strip().lower()),
    )


def _get_owner_type_label(product: dict) -> str:
    owner_role = str(((product.get("owner") or {}).get("role", ""))).strip().lower()
    for label, value in OWNER_TYPES.items():
        if value == owner_role:
            return label
    return "Merchant"


def _build_category_index(category_rows: list[dict]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for row in category_rows:
        category = str(row.get("category", "")).strip()
        if not category:
            continue
        subcategories = [
            str(subcategory).strip()
            for subcategory in (row.get("subcategories", []) or [])
            if str(subcategory).strip()
        ]
        index[category] = subcategories
    return index


def _merge_category_catalog(category_rows: list[dict]) -> dict:
    merged: dict[str, list[str]] = _build_category_index(category_rows)
    for row in MASTER_CATEGORY_ROWS:
        category = row["category"]
        existing = set(merged.get(category, []))
        for subcategory in row["subcategories"]:
            if subcategory not in existing:
                merged.setdefault(category, []).append(subcategory)
    normalized_rows = [
        {"category": category, "subcategories": merged[category]}
        for category in sorted(merged.keys())
    ]
    return {
        "schema_version": 1,
        "categories": normalized_rows,
    }


def _validate_category_selection(category: str, subcategory: str, category_index: dict[str, list[str]]) -> None:
    normalized_category = str(category).strip()
    normalized_subcategory = str(subcategory).strip()
    if normalized_category not in category_index:
        raise ValueError("Invalid category/subcategory selection.")
    if normalized_subcategory not in category_index.get(normalized_category, []):
        raise ValueError("Invalid category/subcategory selection.")


def _ordered_product_images(images: list[dict]) -> list[dict]:
    rows = [dict(image or {}) for image in (images or [])]
    return sorted(rows, key=lambda image: (not bool(image.get("is_primary")), str(image.get("file_name", ""))))


def _render_product_image_gallery(images: list[dict], media_service: MediaService, *, title: str) -> None:
    ordered_images = _ordered_product_images(images)
    if not ordered_images:
        st.info("No product images available.")
        return
    st.markdown(f"#### {title}")
    preview_columns = st.columns(3)
    for index, image in enumerate(ordered_images):
        with preview_columns[index % 3]:
            renderable = media_service.get_renderable_image(image)
            if renderable.get("render_mode") == "bytes" and renderable.get("bytes"):
                st.image(renderable["bytes"], use_container_width=True)
            elif renderable.get("render_mode") == "url" and renderable.get("url"):
                st.image(renderable["url"], use_container_width=True)
            else:
                st.caption("Image unavailable")
            st.caption(image.get("file_name", image.get("image_id", "Image")))
            if image.get("is_primary"):
                st.caption("Primary image")


def _owner_option_label(owner: dict) -> str:
    display_name = str(owner.get("display_name", "")).strip()
    email = str(owner.get("email", "")).strip().lower()
    return f"{display_name} ({email})" if display_name else email


def _delivery_partner_candidates_for_owner(users: list[dict], products: list[dict], owner_email: str) -> list[dict]:
    normalized_owner_email = str(owner_email or "").strip().lower()
    candidate_map: dict[str, dict] = {
        str(user.get("email", "")).strip().lower(): dict(user)
        for user in _active_users_for_role(users, "worker")
    }
    if normalized_owner_email:
        for product in products:
            if str(((product.get("owner") or {}).get("email", ""))).strip().lower() != normalized_owner_email:
                continue
            delivery_partner = dict(product.get("delivery_partner", {}) or {})
            partner_email = str(delivery_partner.get("email", "")).strip().lower()
            if not partner_email:
                continue
            if partner_email not in candidate_map:
                candidate_map[partner_email] = {
                    "user_id": str(delivery_partner.get("user_id", "")).strip(),
                    "email": partner_email,
                    "role": "worker",
                    "status": "ACTIVE",
                    "display_name": str(delivery_partner.get("display_name", "")).strip(),
                    "phone": str(delivery_partner.get("phone", "")).strip(),
                    "source": "owner_delivery_partner_fallback",
                }
    return sorted(
        candidate_map.values(),
        key=lambda user: (str(user.get("display_name", "")).strip().lower(), str(user.get("email", "")).strip().lower()),
    )


def _normalize_owner_business_details(details: dict) -> dict:
    payload = dict(details or {})
    normalized = {
        "business_name": str(payload.get("business_name", "")).strip(),
        "upi_id": str(payload.get("upi_id", "")).strip(),
        "gst_number": str(payload.get("gst_number", "")).strip(),
        "invoice_name": str(payload.get("invoice_name", "")).strip(),
        "invoice_address": str(payload.get("invoice_address", "")).strip(),
        "invoice_phone": str(payload.get("invoice_phone", "")).strip(),
        "bank_account_name": str(payload.get("bank_account_name", "")).strip(),
        "bank_account_number": str(payload.get("bank_account_number", "")).strip(),
        "bank_ifsc": str(payload.get("bank_ifsc", "")).strip(),
        "other_details": str(payload.get("other_details", "")).strip(),
    }
    normalized["profile_completed"] = all(
        normalized[field] for field in ("business_name", "upi_id", "gst_number", "invoice_name")
    )
    return normalized


def _normalize_service_config(details: dict) -> dict:
    payload = dict(details or {})
    return {
        "packaging_mode": str(payload.get("packaging_mode", "owner") or "owner").strip().lower(),
        "shipping_mode": str(payload.get("shipping_mode", "owner") or "owner").strip().lower(),
        "delivery_scope": str(payload.get("delivery_scope", "custom") or "custom").strip().lower(),
        "packaging_cost_b2c": round(float(payload.get("packaging_cost_b2c", 0) or 0), 2),
        "packaging_cost_b2b": round(float(payload.get("packaging_cost_b2b", 0) or 0), 2),
        "shipping_cost_b2c": round(float(payload.get("shipping_cost_b2c", 0) or 0), 2),
        "shipping_cost_b2b": round(float(payload.get("shipping_cost_b2b", 0) or 0), 2),
        "delivery_notes": str(payload.get("delivery_notes", "") or "").strip(),
    }


@contextmanager
def _render_onboarding_section(title: str, caption: str = "", *, eyebrow: str = "Onboarding"):
    render_template(
        "onboarding_section_open.html",
        eyebrow=eyebrow,
        title=title,
        subtitle=caption,
    )
    try:
        with st.container():
            yield
    finally:
        render_template("onboarding_section_close.html")


def _render_consent_panel(
    *,
    product_consent_service: ProductConsentService,
    product_name: str,
    recipient_email: str,
    requested_by: str,
    consent_role: str,
    title: str,
    recipient_label: str,
    session_prefix: str,
) -> dict:
    consent_identity = f"{consent_role}||{product_name.strip().lower()}||{recipient_email.strip().lower()}||{requested_by.strip().lower()}"
    auto_trigger_key = f"{session_prefix}_auto_trigger"
    auto_trigger_status_key = f"{session_prefix}_auto_trigger_status"
    consent_error_key = f"{session_prefix}_error"
    consent_record = product_consent_service.get_consent_status(
        product_name=product_name.strip(),
        owner_email=recipient_email,
        requested_by=requested_by,
        consent_role=consent_role,
    )
    if product_name.strip() and recipient_email.strip() and st.session_state.get(auto_trigger_key) != consent_identity:
        try:
            consent_record = product_consent_service.send_consent_otp(
                product_name=product_name.strip(),
                owner_email=recipient_email,
                requested_by=requested_by,
                consent_role=consent_role,
            )
            st.session_state[auto_trigger_key] = consent_identity
            st.session_state[auto_trigger_status_key] = f"Consent OTP triggered to {recipient_email}."
            st.session_state[consent_error_key] = ""
            st.rerun()
        except Exception as exc:
            st.session_state[consent_error_key] = f"Consent OTP trigger failed: {exc}"
    with st.container():
        st.markdown(f"#### {title}")
        st.caption(
            "OTP is triggered automatically after the email is entered. "
            "Enter the OTP below after the recipient receives the email."
        )
        trigger_status_message = str(st.session_state.get(auto_trigger_status_key, "") or "").strip()
        trigger_error_message = str(st.session_state.get(consent_error_key, "") or "").strip()
        if trigger_status_message and st.session_state.get(auto_trigger_key) == consent_identity:
            st.success(trigger_status_message)
        if trigger_error_message and st.session_state.get(auto_trigger_key) != consent_identity:
            st.error(trigger_error_message)
        current_consent_status = str(consent_record.get("status", "NOT_SENT") or "NOT_SENT").upper()
        status_cols = st.columns([1.4, 2.6, 1.2])
        status_cols[0].caption(f"Status: {current_consent_status}")
        status_cols[1].caption(f"{recipient_label}: {recipient_email}")
        otp_enabled = current_consent_status in {"OTP_SENT", "VERIFIED"}
        entered_otp = status_cols[1].text_input(
            "Consent OTP",
            key=f"{session_prefix}_otp",
            max_chars=8,
            disabled=not otp_enabled,
            label_visibility="collapsed",
            placeholder="Enter OTP",
        )
        if status_cols[2].button("Verify", use_container_width=True, key=f"{session_prefix}_verify", disabled=not otp_enabled):
            try:
                consent_record = product_consent_service.verify_consent_otp(
                    product_name=product_name.strip(),
                    owner_email=recipient_email,
                    requested_by=requested_by,
                    otp_code=entered_otp,
                    consent_role=consent_role,
                )
                st.success(f"{title} verified.")
                st.rerun()
            except Exception as exc:
                st.error(f"Consent OTP verification failed: {exc}")
    return consent_record


def _build_product_table_rows(products: list[dict]) -> list[dict]:
    rows = []
    for product in products:
        rows.append(
            {
                "product_code": product.get("product_code", ""),
                "product_name": product.get("product_name", ""),
                "owner_email": ((product.get("owner") or {}).get("email", "")),
                "owner_role": ((product.get("owner") or {}).get("role", "")),
                "delivery_partner_email": ((product.get("delivery_partner") or {}).get("email", "")),
                "category": product.get("category", ""),
                "subcategory": product.get("subcategory", ""),
                "admin_price": ((product.get("pricing") or {}).get("admin_price", 0)),
                "marketplace_price": ((product.get("pricing") or {}).get("marketplace_price", 0)),
                "manditrade_price": ((product.get("pricing") or {}).get("manditrade_price", 0)),
                "packaging_mode": ((product.get("service_config") or {}).get("packaging_mode", "owner")),
                "shipping_mode": ((product.get("service_config") or {}).get("shipping_mode", "owner")),
                "packaging_cost_b2c": ((product.get("service_config") or {}).get("packaging_cost_b2c", 0)),
                "shipping_cost_b2c": ((product.get("service_config") or {}).get("shipping_cost_b2c", 0)),
                "manditrade_minimum_quantity": (((product.get("sales_channels") or {}).get("manditrade") or {}).get("minimum_quantity", 1)),
                "manditrade_increment_quantity": (((product.get("sales_channels") or {}).get("manditrade") or {}).get("increment_quantity", 1)),
                "quantity": ((product.get("inventory") or {}).get("available_quantity", 0)),
                "status": product.get("status", "ACTIVE"),
            }
        )
    return rows


def _archive_product(products: list[dict], product_id: str, current_user_email: str) -> None:
    for product in products:
        if product.get("product_id") == product_id:
            product["status"] = "ARCHIVED"
            product["updated_at"] = datetime.now(UTC).isoformat()
            product["updated_by"] = current_user_email
            return


def _delete_product(products: list[dict], product_id: str) -> bool:
    initial_count = len(products)
    products[:] = [product for product in products if str(product.get("product_id", "")).strip() != str(product_id).strip()]
    return len(products) != initial_count


def _resolve_or_create_owner(
    *,
    users: list[dict],
    owner_email: str,
    owner_role: str,
    owner_display_name: str,
    owner_phone: str,
    current_user_email: str,
    data_service,
    id_service: IdService,
) -> tuple[dict, bool]:
    normalized_email = owner_email.strip().lower()
    if not normalized_email:
        raise ValueError("Owner email is required.")
    existing = next((user for user in users if str(user.get("email", "")).strip().lower() == normalized_email), None)
    if existing:
        existing_role = str(existing.get("role", "")).strip().lower()
        if existing_role != owner_role:
            raise ValueError(
                f"Owner email already exists with role {existing_role or 'unknown'}. Cannot assign as {owner_role}."
            )
        existing["status"] = "ACTIVE"
        if owner_display_name.strip() and not str(existing.get("display_name", "")).strip():
            existing["display_name"] = owner_display_name.strip()
        if owner_phone.strip() and not str(existing.get("phone", "")).strip():
            existing["phone"] = owner_phone.strip()
        return existing, False
    user_id = id_service.next_drive_id(data_service.admin_drive_service, "user", "USR")
    new_user = {
        "user_id": user_id,
        "email": normalized_email,
        "role": owner_role,
        "status": "ACTIVE",
        "display_name": "",
        "phone": owner_phone.strip(),
        "source": "product_onboarding",
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": current_user_email,
    }
    if owner_display_name.strip():
        new_user["display_name"] = owner_display_name.strip()
    data_service.upsert_user(new_user)
    return new_user, True


def _apply_product_values(
    *,
    product: dict,
    product_code: str,
    owner: dict,
    values: dict,
    current_user_email: str,
    uploaded_images: list[dict] | None = None,
) -> None:
    images = list(uploaded_images if uploaded_images is not None else product.get("images", []) or [])
    primary_image = next((image for image in images if image.get("is_primary")), images[0] if images else {})
    product["product_id"] = product_code
    product["product_code"] = product_code
    product["product_name"] = values["product_name"]
    product["status"] = values["status"]
    product["owner"] = {
        "email": values["owner_email"],
        "role": owner.get("role", ""),
        "display_name": owner.get("display_name", values["owner_email"].split("@")[0]),
        "user_id": owner.get("user_id", ""),
        "phone": owner.get("phone", values.get("owner_phone", "")),
    }
    owner_business_details = dict(values.get("owner_business_details", {}) or {})
    owner_profile_completed = bool(owner_business_details.get("profile_completed", False))
    product["posting_status"] = "READY_TO_POST" if owner_profile_completed else "DUE_FOR_POSTING"
    product["owner_business_details"] = owner_business_details
    product["shipment_management"] = {
        "managed_by_owner": bool(values.get("managed_by_owner", True)),
        "preferred_delivery_partner_email": str((((values.get("delivery_partner", {}) or {}).get("email", "")))).strip().lower(),
    }
    delivery_partner = dict(values.get("delivery_partner", {}) or {})
    product["delivery_partner"] = {
        "email": str(delivery_partner.get("email", "")).strip().lower(),
        "role": "worker" if str(delivery_partner.get("email", "")).strip() else "",
        "display_name": str(delivery_partner.get("display_name", "")).strip(),
        "user_id": str(delivery_partner.get("user_id", "")).strip(),
        "phone": str(delivery_partner.get("phone", "")).strip(),
    }
    product["category"] = values["category"]
    product["subcategory"] = values["subcategory"]
    product["description"] = values["description"]
    product["images"] = images
    product["image_url"] = (
        primary_image.get("image_url")
        or primary_image.get("thumbnail_link")
        or primary_image.get("web_view_link")
        or ""
    )
    product["unit"] = values["unit"]
    product["pricing"] = {
        "admin_price": values["admin_price"],
        "marketplace_price": values["marketplace_price"],
        "manditrade_price": values["manditrade_price"],
        "currency": "INR",
    }
    product["service_config"] = _normalize_service_config(values.get("service_config", {}))
    product["sales_channels"] = {
        "marketplace": {
            "enabled": values["marketplace_enabled"],
            "minimum_quantity": 1.0,
            "increment_quantity": 1.0,
        },
        "manditrade": {
            "enabled": values["manditrade_enabled"],
            "minimum_quantity": values["manditrade_minimum_quantity"],
            "increment_quantity": values["manditrade_increment_quantity"],
        },
    }
    product["inventory"] = {
        "available_quantity": values["available_quantity"],
        "manual_update_only": True,
    }
    product["approval"] = dict(product.get("approval", {}) or {})
    product["approval"]["submitted_by"] = values.get("submitted_by", product["approval"].get("submitted_by", current_user_email))
    product["approval"]["submitted_at"] = values.get("submitted_at", product["approval"].get("submitted_at", datetime.now(UTC).isoformat()))
    product["updated_at"] = datetime.now(UTC).isoformat()
    product["updated_by"] = current_user_email


def _persist_products_and_users(data_service) -> None:
    data_service.persist_collection("users")
    data_service.persist_collection("products")


def _persist_notifications(data_service) -> None:
    data_service.persist_collection("notifications")
    data_service.persist_collection("gmail_queue")


def _get_editable_status_options(is_admin: bool, current_status: str) -> list[str]:
    if is_admin:
        return STATUSES
    normalized_status = str(current_status or "PENDING_APPROVAL").upper()
    return [normalized_status or "PENDING_APPROVAL"]


def render_products_page(data_service, notification_service, session_service, cache_service, translator) -> None:
    products = data_service.get_collection_ref("products")
    users = data_service.get_collection_ref("users")
    app_config = dict(cache_service.get_config("app_config") or {})
    ui_config = dict(app_config.get("ui", {}) or {})
    categories_config = cache_service.get_config("categories")
    merged_categories_payload = _merge_category_catalog(categories_config.get("categories", []))
    category_rows = merged_categories_payload.get("categories", [])
    category_index = _build_category_index(category_rows)
    category_names = list(category_index.keys())
    current_user_email = session_service.get_user().get("email", "")
    current_user_role = session_service.get_user().get("role", "")
    is_admin = current_user_role == "platform_admin" or is_bootstrap_admin(current_user_email)
    current_user_record = next((row for row in users if str(row.get("email", "")).strip().lower() == str(current_user_email).strip().lower()), {})
    if merged_categories_payload != categories_config and current_user_role == "platform_admin":
        try:
            data_service.admin_drive_service.write_json("00_config/categories.json", merged_categories_payload)
            cache_service.update_config("categories", merged_categories_payload)
        except Exception:
            pass
    visible_products = (
        products
        if is_admin
        else [product for product in products if str(((product.get("owner") or {}).get("email", ""))).strip().lower() == str(current_user_email).strip().lower()]
    )
    id_service = IdService()
    media_service = MediaService(data_service.admin_drive_service)
    product_consent_service = ProductConsentService(data_service, cache_service)
    next_product_code = id_service.preview_drive_id(data_service.admin_drive_service, "product", "PROD")
    tab_labels = ["All Products", "Marketplace", "MandiTrade", "Pending Approval", "Approved", "Inactive/Archived", "Add Product"]
    if is_admin:
        tab_labels.append("Approve Products")
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_table(_build_product_table_rows(visible_products), caption="All products")
        active_product_ids = [product.get("product_id", "") for product in visible_products if str(product.get("product_id", "")).strip()]
        if active_product_ids:
            product_action_cols = st.columns(2 if is_admin else 1)
            archive_product_id = product_action_cols[0].selectbox(translator.t("action.archive"), options=[""] + active_product_ids, key="archive_product_id")
            if product_action_cols[0].button(translator.t("action.archive"), use_container_width=True) and archive_product_id:
                _archive_product(products, archive_product_id, current_user_email)
                try:
                    data_service.persist_collection("products")
                    data_service.cache_service.refresh_cache()
                    st.success("Product archived.")
                except Exception as exc:
                    st.error(f"Drive write failed: {exc}")
            if is_admin:
                delete_product_id = product_action_cols[1].selectbox("Delete Product", options=[""] + active_product_ids, key="delete_product_id")
                if product_action_cols[1].button("Delete Product", use_container_width=True, type="primary") and delete_product_id:
                    previous_products_snapshot = deepcopy(products)
                    if _delete_product(products, delete_product_id):
                        try:
                            data_service.persist_collection("products")
                            data_service.cache_service.refresh_cache()
                            st.success(f"Product {delete_product_id} deleted.")
                            st.rerun()
                        except Exception as exc:
                            products.clear()
                            products.extend(previous_products_snapshot)
                            st.error(f"Drive write failed: {exc}")
        editable_ids = [product.get("product_id", "") for product in visible_products]
        if editable_ids:
            selected_edit_id = st.selectbox(translator.t("module.products.title"), options=[""] + editable_ids, key="edit_product_id")
            selected_product = next((product for product in visible_products if product.get("product_id") == selected_edit_id), None)
            if selected_product:
                existing_images = _ordered_product_images(selected_product.get("images", []) or [])
                selected_owner = dict(selected_product.get("owner", {}) or {})
                selected_owner_role = str(selected_owner.get("role", OWNER_TYPES[_get_owner_type_label(selected_product)])).strip().lower()
                owner_type_label = next((label for label, role in OWNER_TYPES.items() if role == selected_owner_role), "Manufacturer")
                owner_options = _owner_candidates_for_role(users, products, OWNER_TYPES[owner_type_label])
                existing_owner_values = [row.get("email", "") for row in owner_options]
                default_owner_mode = "Select Existing" if str(selected_owner.get("email", "")).strip().lower() in {str(value).strip().lower() for value in existing_owner_values} else "Add New"
                st.caption(f"Product Code: {selected_product.get('product_code', '')}")
                if existing_images:
                    _render_product_image_gallery(existing_images, media_service, title="Current Product Images")
                edit_product_name = st.text_input(translator.t("field.product_name"), value=selected_product.get("product_name", ""), key="edit_product_name")
                edit_owner_email = str(selected_owner.get("email", "")).strip().lower()
                edit_owner_display_name = str(selected_owner.get("display_name", "")).strip()
                edit_owner_phone = str(selected_owner.get("phone", "")).strip()
                selected_delivery_partner = dict(selected_product.get("delivery_partner", {}) or {})
                edit_delivery_partner_email = str(selected_delivery_partner.get("email", "")).strip().lower()
                edit_delivery_partner_display_name = str(selected_delivery_partner.get("display_name", "")).strip()
                edit_delivery_partner_phone = str(selected_delivery_partner.get("phone", "")).strip()
                if is_admin:
                    edit_owner_type = st.selectbox(
                        translator.t("field.owner_type"),
                        options=list(OWNER_TYPES.keys()),
                        index=list(OWNER_TYPES.keys()).index(owner_type_label),
                        key="edit_owner_type",
                    )
                    edit_owner_mode = st.radio(
                        "Owner Selection Mode",
                        options=["Select Existing", "Add New"],
                        horizontal=True,
                        index=0 if default_owner_mode == "Select Existing" else 1,
                        key="edit_owner_mode",
                    )
                    edit_role_key = OWNER_TYPES[edit_owner_type]
                    edit_owner_candidates = _owner_candidates_for_role(users, products, edit_role_key)
                    if edit_owner_mode == "Select Existing" and edit_owner_candidates:
                        edit_owner_option_map = {row.get("email", ""): row for row in edit_owner_candidates}
                        edit_owner_choice = st.selectbox(
                            translator.t("field.owner_email"),
                            options=list(edit_owner_option_map.keys()),
                            format_func=lambda value: _owner_option_label(edit_owner_option_map.get(value, {})),
                            index=next((idx for idx, value in enumerate(edit_owner_option_map.keys()) if str(value).strip().lower() == edit_owner_email), 0),
                            key="edit_existing_owner",
                        )
                        selected_existing_owner = edit_owner_option_map.get(edit_owner_choice, {})
                        edit_owner_email = str(selected_existing_owner.get("email", edit_owner_email)).strip().lower()
                        edit_owner_display_name = str(selected_existing_owner.get("display_name", edit_owner_display_name)).strip()
                        edit_owner_phone = str(selected_existing_owner.get("phone", edit_owner_phone)).strip()
                        st.caption(f"Selected Owner: {_owner_option_label(selected_existing_owner)}")
                    else:
                        if edit_owner_mode == "Select Existing" and not edit_owner_candidates:
                            st.info("No existing active owners found for this role. Add a new owner.")
                        edit_owner_email = st.text_input(translator.t("field.owner_email"), value=edit_owner_email, key="edit_owner_email").strip().lower()
                        edit_owner_display_name = st.text_input("Owner Display Name", value=edit_owner_display_name, key="edit_owner_display_name")
                        edit_owner_phone = st.text_input("Owner Phone", value=edit_owner_phone, key="edit_owner_phone")
                    edit_delivery_partner_mode = st.radio(
                        "Worker Selection",
                        options=["Select Existing", "Add New"],
                        horizontal=True,
                        index=0 if edit_delivery_partner_email else 1,
                        key="edit_delivery_partner_mode",
                    )
                    edit_delivery_partner_candidates = _owner_candidates_for_role(users, products, "worker")
                    if edit_delivery_partner_mode == "Select Existing" and edit_delivery_partner_candidates:
                        edit_partner_map = {row.get("email", ""): row for row in edit_delivery_partner_candidates}
                        edit_partner_choice = st.selectbox(
                            "Worker Email",
                            options=list(edit_partner_map.keys()),
                            format_func=lambda value: _owner_option_label(edit_partner_map.get(value, {})),
                            index=next((idx for idx, value in enumerate(edit_partner_map.keys()) if str(value).strip().lower() == edit_delivery_partner_email), 0),
                            key="edit_existing_delivery_partner",
                        )
                        selected_partner = edit_partner_map.get(edit_partner_choice, {})
                        edit_delivery_partner_email = str(selected_partner.get("email", "")).strip().lower()
                        edit_delivery_partner_display_name = str(selected_partner.get("display_name", "")).strip()
                        edit_delivery_partner_phone = str(selected_partner.get("phone", "")).strip()
                        st.caption(f"Selected Worker: {_owner_option_label(selected_partner)}")
                    else:
                        if edit_delivery_partner_mode == "Select Existing" and not edit_delivery_partner_candidates:
                            st.info("No existing active workers found. Add a new worker.")
                        edit_delivery_partner_email = st.text_input("Worker Email", value=edit_delivery_partner_email, key="edit_delivery_partner_email").strip().lower()
                        edit_delivery_partner_display_name = st.text_input("Worker Name", value=edit_delivery_partner_display_name, key="edit_delivery_partner_display_name")
                        edit_delivery_partner_phone = st.text_input("Worker Phone", value=edit_delivery_partner_phone, key="edit_delivery_partner_phone")
                else:
                    edit_role_key = current_user_role
                    edit_owner_email = str(current_user_email).strip().lower()
                    edit_owner_display_name = str(current_user_record.get("display_name", edit_owner_display_name)).strip()
                    edit_owner_phone = str(current_user_record.get("phone", edit_owner_phone)).strip()
                    edit_delivery_partner_email = str(selected_delivery_partner.get("email", "")).strip().lower()
                    edit_delivery_partner_display_name = str(selected_delivery_partner.get("display_name", "")).strip()
                    edit_delivery_partner_phone = str(selected_delivery_partner.get("phone", "")).strip()
                    st.caption(f"Owner: {edit_owner_email}")
                    st.caption(f"Owner Role: {edit_role_key}")
                edit_category = st.selectbox(
                    translator.t("field.category"),
                    options=category_names if category_names else [""],
                    index=category_names.index(selected_product.get("category", "")) if selected_product.get("category", "") in category_names else 0,
                    key="edit_category",
                )
                edit_subcategories = category_index.get(edit_category, [])
                current_edit_subcategory = selected_product.get("subcategory", "")
                if current_edit_subcategory not in edit_subcategories:
                    current_edit_subcategory = edit_subcategories[0] if edit_subcategories else ""
                edit_subcategory = st.selectbox(
                    translator.t("field.subcategory"),
                    options=edit_subcategories if edit_subcategories else [""],
                    index=edit_subcategories.index(current_edit_subcategory) if current_edit_subcategory in edit_subcategories else 0,
                    key="edit_subcategory",
                )
                edit_description = st.text_area(translator.t("field.description"), value=selected_product.get("description", ""), key="edit_description")
                edit_unit = st.text_input(translator.t("field.unit"), value=selected_product.get("unit", "piece"), key="edit_unit")
                edit_available_quantity = st.number_input(translator.t("field.quantity"), min_value=0.0, step=1.0, value=float((selected_product.get("inventory") or {}).get("available_quantity", 0)), key="edit_available_quantity")
                edit_marketplace_enabled = st.checkbox(translator.t("field.available_marketplace"), value=((selected_product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled", False), key="edit_marketplace_enabled")
                edit_admin_price = st.number_input(translator.t("field.admin_price"), min_value=0.0, step=1.0, value=float(((selected_product.get("pricing") or {}).get("admin_price", 0))), key="edit_admin_price")
                edit_marketplace_price = st.number_input(translator.t("field.marketplace_price"), min_value=0.0, step=1.0, value=float(((selected_product.get("pricing") or {}).get("marketplace_price", 0))), key="edit_marketplace_price")
                edit_manditrade_enabled = st.checkbox(translator.t("field.available_manditrade"), value=((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled", False), key="edit_manditrade_enabled")
                edit_manditrade_price = st.number_input(translator.t("field.manditrade_price"), min_value=0.0, step=1.0, value=float(((selected_product.get("pricing") or {}).get("manditrade_price", 0))), key="edit_manditrade_price")
                edit_manditrade_minimum_quantity = st.number_input(
                    translator.t("field.manditrade_minimum_quantity"),
                    min_value=1.0,
                    step=1.0,
                    value=float((((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("minimum_quantity", 1)) or 1),
                    key="edit_manditrade_minimum_quantity",
                )
                edit_manditrade_increment_quantity = st.number_input(
                    translator.t("field.manditrade_increment_quantity"),
                    min_value=1.0,
                    step=1.0,
                    value=float((((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("increment_quantity", 1)) or 1),
                    key="edit_manditrade_increment_quantity",
                )
                selected_service_config = _normalize_service_config(selected_product.get("service_config", {}) or {})
                st.markdown("#### Fulfillment Services")
                service_cols = st.columns(3)
                edit_packaging_mode = service_cols[0].selectbox("Packaging Mode", options=["owner", "manditrade"], index=["owner", "manditrade"].index(selected_service_config.get("packaging_mode", "owner")), key="edit_packaging_mode")
                edit_shipping_mode = service_cols[1].selectbox("Shipping Mode", options=["owner", "manditrade"], index=["owner", "manditrade"].index(selected_service_config.get("shipping_mode", "owner")), key="edit_shipping_mode")
                edit_delivery_scope = service_cols[2].selectbox("Delivery Scope", options=["custom", "local", "zonal", "national"], index=["custom", "local", "zonal", "national"].index(selected_service_config.get("delivery_scope", "custom")) if selected_service_config.get("delivery_scope", "custom") in ["custom", "local", "zonal", "national"] else 0, key="edit_delivery_scope")
                service_cost_cols = st.columns(4)
                edit_packaging_cost_b2c = service_cost_cols[0].number_input("Packaging Cost B2C", min_value=0.0, step=1.0, value=float(selected_service_config.get("packaging_cost_b2c", 0) or 0), key="edit_packaging_cost_b2c")
                edit_shipping_cost_b2c = service_cost_cols[1].number_input("Shipping Cost B2C", min_value=0.0, step=1.0, value=float(selected_service_config.get("shipping_cost_b2c", 0) or 0), key="edit_shipping_cost_b2c")
                edit_packaging_cost_b2b = service_cost_cols[2].number_input("Packaging Cost B2B", min_value=0.0, step=1.0, value=float(selected_service_config.get("packaging_cost_b2b", 0) or 0), key="edit_packaging_cost_b2b")
                edit_shipping_cost_b2b = service_cost_cols[3].number_input("Shipping Cost B2B", min_value=0.0, step=1.0, value=float(selected_service_config.get("shipping_cost_b2b", 0) or 0), key="edit_shipping_cost_b2b")
                edit_delivery_notes = st.text_area("Fulfillment Notes", value=str(selected_service_config.get("delivery_notes", "") or ""), key="edit_delivery_notes", height=80)
                editable_statuses = _get_editable_status_options(is_admin, selected_product.get("status", "PENDING_APPROVAL"))
                edit_status = st.selectbox(translator.t("field.status"), options=editable_statuses, index=editable_statuses.index(str(selected_product.get("status", editable_statuses[0])).upper()) if str(selected_product.get("status", editable_statuses[0])).upper() in editable_statuses else 0, key="edit_status")
                edit_uploaded_files = st.file_uploader(
                    translator.t("field.product_images"),
                    accept_multiple_files=True,
                    type=["png", "jpg", "jpeg", "webp"],
                    key="edit_product_images",
                )
                updated = st.button(translator.t("action.save"), use_container_width=True, key="update_product_button")
                if updated:
                    if not edit_product_name.strip():
                        st.error("Product name is required.")
                        return
                    previous_product_snapshot = deepcopy(selected_product)
                    previous_users_snapshot = deepcopy(users)
                    try:
                        _validate_category_selection(edit_category, edit_subcategory, category_index)
                        owner, _ = _resolve_or_create_owner(
                            users=users,
                            owner_email=edit_owner_email,
                            owner_role=edit_role_key,
                            owner_display_name=edit_owner_display_name,
                            owner_phone=edit_owner_phone,
                            current_user_email=current_user_email,
                            data_service=data_service,
                            id_service=id_service,
                        )
                        delivery_partner = {}
                        if edit_delivery_partner_email:
                            delivery_partner, _ = _resolve_or_create_owner(
                                users=users,
                                owner_email=edit_delivery_partner_email,
                                owner_role="worker",
                                owner_display_name=edit_delivery_partner_display_name,
                                owner_phone=edit_delivery_partner_phone,
                                current_user_email=current_user_email,
                                data_service=data_service,
                                id_service=id_service,
                            )
                        uploaded_images = existing_images
                        if edit_uploaded_files:
                            uploaded_images = media_service.upload_product_images(
                                edit_uploaded_files,
                                uploaded_by=current_user_email,
                                product_code=selected_product.get("product_code", selected_product.get("product_id", "PROD")),
                            )
                            for image in uploaded_images:
                                media_service.clear_cached_image(str(image.get("file_id", "")))
                        _apply_product_values(
                            product=selected_product,
                            product_code=selected_product.get("product_code", selected_product.get("product_id", "")),
                            owner=owner,
                            values={
                                "product_name": edit_product_name.strip(),
                                "owner_email": edit_owner_email,
                                "owner_phone": edit_owner_phone.strip(),
                                "category": edit_category,
                                "subcategory": edit_subcategory,
                                "description": edit_description.strip(),
                                "unit": edit_unit.strip() or "piece",
                                "available_quantity": edit_available_quantity,
                                "admin_price": edit_admin_price,
                                "marketplace_enabled": edit_marketplace_enabled,
                                "marketplace_price": edit_marketplace_price,
                                "manditrade_enabled": edit_manditrade_enabled,
                                "manditrade_price": edit_manditrade_price,
                                "manditrade_minimum_quantity": edit_manditrade_minimum_quantity,
                                "manditrade_increment_quantity": edit_manditrade_increment_quantity,
                                "service_config": {
                                    "packaging_mode": edit_packaging_mode,
                                    "shipping_mode": edit_shipping_mode,
                                    "delivery_scope": edit_delivery_scope,
                                    "packaging_cost_b2c": edit_packaging_cost_b2c,
                                    "shipping_cost_b2c": edit_shipping_cost_b2c,
                                    "packaging_cost_b2b": edit_packaging_cost_b2b,
                                    "shipping_cost_b2b": edit_shipping_cost_b2b,
                                    "delivery_notes": edit_delivery_notes,
                                },
                                "status": edit_status if is_admin else "PENDING_APPROVAL",
                                "delivery_partner": delivery_partner,
                                "submitted_by": (selected_product.get("approval") or {}).get("submitted_by", selected_product.get("created_by", current_user_email)),
                                "submitted_at": (selected_product.get("approval") or {}).get("submitted_at", selected_product.get("created_at", datetime.now(UTC).isoformat())),
                            },
                            current_user_email=current_user_email,
                            uploaded_images=uploaded_images,
                        )
                        if str(selected_product.get("status", "")).upper() == "APPROVED":
                            selected_product["approval"]["approved_by"] = current_user_email
                            selected_product["approval"]["approved_at"] = datetime.now(UTC).isoformat()
                        _persist_products_and_users(data_service)
                        st.success("Product updated.")
                    except Exception as exc:
                        selected_product.clear()
                        selected_product.update(previous_product_snapshot)
                        users.clear()
                        users.extend(previous_users_snapshot)
                        st.error(f"Drive write failed: {exc}")

    with tabs[1]:
        render_product_grid(
            [
                product
                for product in visible_products
                if ((product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled")
                and str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"
            ],
            view="admin",
            media_service=media_service,
            return_route="products",
            grid_context="products_marketplace_tab",
            translator=translator,
            ui_config=ui_config,
        )

    with tabs[2]:
        render_product_grid(
            [
                product
                for product in visible_products
                if ((product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled")
                and str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"
            ],
            view="admin",
            media_service=media_service,
            return_route="products",
            grid_context="products_manditrade_tab",
            translator=translator,
            ui_config=ui_config,
        )

    with tabs[3]:
        render_table(
            _build_product_table_rows(
                [product for product in visible_products if str(product.get("status", "PENDING_APPROVAL")).upper() == "PENDING_APPROVAL"]
            ),
            caption="Pending approval products",
        )

    with tabs[4]:
        render_table(
            _build_product_table_rows(
                [product for product in visible_products if str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"]
            ),
            caption="Approved products",
        )

    with tabs[5]:
        render_table(
            _build_product_table_rows(
                [product for product in visible_products if str(product.get("status", "PENDING_APPROVAL")).upper() in {"REJECTED", "ARCHIVED"}]
            ),
            caption="Inactive / archived products",
        )

    with tabs[6]:
        render_template(
            "onboarding_section_open.html",
            eyebrow="Catalog",
            title="Product Onboarding",
            subtitle="Set up the owner, billing details, shipment handling, catalog details, and channel pricing in one guided flow.",
        )
        st.caption(f"Product Code: {next_product_code}")
        render_template("onboarding_section_close.html")
        create_tabs = st.tabs(
            [
                "1. Basics",
                "2. Owner",
                "3. Delivery",
                "4. Pricing",
                "5. Media",
            ]
        )
        product_name = ""
        if is_admin:
            owner_type = ""
            owner_role_key = ""
            owner_mode = ""
            owner_candidates = []
            owner_email = ""
            owner_display_name = ""
            owner_phone = ""
            delivery_partner_email = ""
            delivery_partner_display_name = ""
            delivery_partner_phone = ""
        else:
            owner_role_key = current_user_role
            owner_email = str(current_user_email).strip().lower()
            owner_display_name = str(current_user_record.get("display_name", "")).strip()
            owner_phone = str(current_user_record.get("phone", "")).strip()
            delivery_partner_email = ""
            delivery_partner_display_name = ""
            delivery_partner_phone = ""
            shipment_management_mode = "Owner Managed"
        with create_tabs[0]:
            with _render_onboarding_section(
                "Product Basics",
                "Start with the product name, category, stock, and description. Keep this part short and clear.",
                eyebrow="Step 1",
            ):
                product_name = st.text_input("Product Name", key="create_product_name", placeholder="Example: Premium Towel Supply")
                basics_cols = st.columns(2)
                category = basics_cols[0].selectbox("Category", options=category_names if category_names else [""], key="create_category")
                subcategories = category_index.get(category, [])
                subcategory = basics_cols[1].selectbox("Subcategory", options=subcategories if subcategories else [""], key="create_subcategory")
                stock_cols = st.columns(2)
                unit = stock_cols[0].text_input("Unit", value="piece", key="create_unit", help="Example: piece, kg, box, bundle")
                available_quantity = stock_cols[1].number_input("Available Quantity", min_value=0.0, step=1.0, key="create_available_quantity")
                description = st.text_area("Description", key="create_description", height=120, placeholder="Write a simple product description for buyers.")

        with create_tabs[1]:
            if is_admin:
                with _render_onboarding_section(
                    "Owner Setup",
                    "Choose an existing merchant, or add a new merchant directly from this form.",
                    eyebrow="Step 2",
                ):
                    owner_cols = st.columns(2)
                    owner_type = owner_cols[0].selectbox("Owner Type", options=list(OWNER_TYPES.keys()), key="create_owner_type")
                    owner_role_key = OWNER_TYPES[owner_type]
                    owner_mode = owner_cols[1].radio("Owner Selection", options=["Select Existing", "Add New"], horizontal=True, key="create_owner_mode")
                    owner_candidates = _owner_candidates_for_role(users, products, owner_role_key)
                    if owner_mode == "Select Existing" and owner_candidates:
                        owner_option_map = {row.get("email", ""): row for row in owner_candidates}
                        owner_choice = st.selectbox(
                            "Owner",
                            options=list(owner_option_map.keys()),
                            format_func=lambda value: _owner_option_label(owner_option_map.get(value, {})),
                            key="create_existing_owner",
                        )
                        selected_owner_row = owner_option_map.get(owner_choice, {})
                        owner_email = str(selected_owner_row.get("email", "")).strip().lower()
                        owner_display_name = str(selected_owner_row.get("display_name", "")).strip()
                        owner_phone = str(selected_owner_row.get("phone", "")).strip()
                        st.caption(f"Selected Owner: {_owner_option_label(selected_owner_row)}")
                    else:
                        if owner_mode == "Select Existing" and not owner_candidates:
                            st.info("No active merchant is available yet. Add a new merchant below.")
                        owner_identity_cols = st.columns(2)
                        owner_email = owner_identity_cols[0].text_input("Owner Email", key="create_owner_email").strip().lower()
                        owner_display_name = owner_identity_cols[1].text_input("Owner Name", key="create_owner_display_name")
                        owner_phone = st.text_input("Owner Phone", key="create_owner_phone")
            else:
                with _render_onboarding_section("Owner Setup", "This product will use your owner account automatically.", eyebrow="Step 2"):
                    owner_preview_cols = st.columns(2)
                    owner_preview_cols[0].caption(f"Owner: {owner_email}")
                    owner_preview_cols[1].caption(f"Owner Role: {owner_role_key}")
        owner_profile_service = UserProfileService(data_service)
        owner_profile_preview = {}
        if owner_email.strip():
            try:
                owner_profile_preview = owner_profile_service.get_profile(owner_email)
            except Exception:
                owner_profile_preview = {}
            if not owner_profile_preview:
                owner_profile_preview = {
                    "email": owner_email,
                    "role": owner_role_key or "public_buyer",
                    "display_name": owner_display_name or owner_email.split("@")[0],
                    "mobile": owner_phone,
                    "details": {},
                }
        owner_details_preview = _normalize_owner_business_details((owner_profile_preview.get("details", {}) if owner_profile_preview else {}) or {})
        owner_identity = f"{owner_role_key}|{owner_email}"
        if st.session_state.get("create_owner_details_identity") != owner_identity:
            st.session_state["create_owner_details_identity"] = owner_identity
            st.session_state["create_owner_business_name"] = owner_details_preview.get("business_name", "")
            st.session_state["create_owner_upi_id"] = owner_details_preview.get("upi_id", "")
            st.session_state["create_owner_gst_number"] = owner_details_preview.get("gst_number", "")
            st.session_state["create_owner_invoice_name"] = owner_details_preview.get("invoice_name", "")
            st.session_state["create_owner_invoice_address"] = owner_details_preview.get("invoice_address", "")
            st.session_state["create_owner_invoice_phone"] = owner_details_preview.get("invoice_phone", "")
            st.session_state["create_owner_bank_account_name"] = owner_details_preview.get("bank_account_name", "")
            st.session_state["create_owner_bank_account_number"] = owner_details_preview.get("bank_account_number", "")
            st.session_state["create_owner_bank_ifsc"] = owner_details_preview.get("bank_ifsc", "")
            st.session_state["create_owner_other_details"] = owner_details_preview.get("other_details", "")
        with create_tabs[1]:
            with _render_onboarding_section(
                "Billing and Invoice Details",
                "These details are saved against the owner and reused the next time this owner adds a product.",
                eyebrow="Step 2",
            ):
                owner_business_cols = st.columns(2)
                owner_business_name = owner_business_cols[0].text_input("Business Name", key="create_owner_business_name")
                owner_upi_id = owner_business_cols[1].text_input("UPI ID", key="create_owner_upi_id")
                owner_tax_cols = st.columns(2)
                owner_gst_number = owner_tax_cols[0].text_input("GST Number", key="create_owner_gst_number")
                owner_invoice_phone = owner_tax_cols[1].text_input("Invoice Contact Phone", key="create_owner_invoice_phone")
                owner_invoice_name = st.text_input("Invoice Name", key="create_owner_invoice_name")
                owner_invoice_address = st.text_area("Invoice Address", key="create_owner_invoice_address", height=90)
                bank_cols = st.columns(2)
                owner_bank_account_name = bank_cols[0].text_input("Bank Account Name", key="create_owner_bank_account_name")
                owner_bank_account_number = bank_cols[1].text_input("Bank Account Number", key="create_owner_bank_account_number")
                owner_bank_ifsc = st.text_input("Bank IFSC", key="create_owner_bank_ifsc")
                owner_other_details = st.text_area("Extra Notes", key="create_owner_other_details", height=90, placeholder="Optional business notes")

        with create_tabs[2]:
            with _render_onboarding_section(
                "Shipment Ownership",
                "Choose whether the owner handles shipment directly or wants a preferred worker saved with this product.",
                eyebrow="Step 3",
            ):
                if is_admin:
                    shipment_management_mode = st.radio(
                        "Shipment Management",
                        options=["Owner Managed", "Owner Preferred Worker"],
                        horizontal=True,
                        key="create_shipment_management_mode",
                    )
                    if shipment_management_mode == "Owner Preferred Worker":
                        delivery_partner_mode = st.radio("Worker Selection", options=["Select Existing", "Add New"], horizontal=True, key="create_delivery_partner_mode")
                        delivery_partner_candidates = _delivery_partner_candidates_for_owner(users, products, owner_email)
                        if delivery_partner_mode == "Select Existing" and delivery_partner_candidates:
                            partner_option_map = {row.get("email", ""): row for row in delivery_partner_candidates}
                            partner_choice = st.selectbox(
                                "Worker",
                                options=list(partner_option_map.keys()),
                                format_func=lambda value: _owner_option_label(partner_option_map.get(value, {})),
                                key="create_existing_delivery_partner",
                            )
                            selected_partner_row = partner_option_map.get(partner_choice, {})
                            delivery_partner_email = str(selected_partner_row.get("email", "")).strip().lower()
                            delivery_partner_display_name = str(selected_partner_row.get("display_name", "")).strip()
                            delivery_partner_phone = str(selected_partner_row.get("phone", "")).strip()
                            st.caption(f"Selected Worker: {_owner_option_label(selected_partner_row)}")
                        else:
                            if delivery_partner_mode == "Select Existing" and not delivery_partner_candidates:
                                st.info("No active worker is linked yet. Add a new preferred worker below.")
                            shipment_partner_cols = st.columns(2)
                            delivery_partner_email = shipment_partner_cols[0].text_input("Worker Email", key="create_delivery_partner_email").strip().lower()
                            delivery_partner_display_name = shipment_partner_cols[1].text_input("Worker Name", key="create_delivery_partner_display_name")
                            delivery_partner_phone = st.text_input("Worker Phone", key="create_delivery_partner_phone")
                    else:
                        st.caption("Owner will manage shipment handling for this product and can assign a worker later per order.")
                else:
                    st.caption("You will manage shipment handling for this product and can assign a worker later per order.")

            with _render_onboarding_section(
                "Fulfillment Services",
                "Set packaging and shipping support clearly for B2C and B2B orders.",
                eyebrow="Step 3",
            ):
                service_mode_cols = st.columns(2)
                packaging_mode = service_mode_cols[0].selectbox("Packaging Mode", options=["owner", "manditrade"], key="create_packaging_mode")
                shipping_mode = service_mode_cols[1].selectbox("Shipping Mode", options=["owner", "manditrade"], key="create_shipping_mode")
                delivery_scope = st.selectbox("Delivery Scope", options=["custom", "local", "zonal", "national"], key="create_delivery_scope")
                b2c_cols = st.columns(2)
                packaging_cost_b2c = b2c_cols[0].number_input("Packaging Cost B2C", min_value=0.0, step=1.0, key="create_packaging_cost_b2c")
                shipping_cost_b2c = b2c_cols[1].number_input("Shipping Cost B2C", min_value=0.0, step=1.0, key="create_shipping_cost_b2c")
                b2b_cols = st.columns(2)
                packaging_cost_b2b = b2b_cols[0].number_input("Packaging Cost B2B", min_value=0.0, step=1.0, key="create_packaging_cost_b2b")
                shipping_cost_b2b = b2b_cols[1].number_input("Shipping Cost B2B", min_value=0.0, step=1.0, key="create_shipping_cost_b2b")
                delivery_notes = st.text_area("Fulfillment Notes", key="create_delivery_notes", height=80)

        with create_tabs[3]:
            with _render_onboarding_section(
                "Pricing and Channels",
                "Choose prices carefully and decide whether this product should be visible in marketplace, mandiplace, or both.",
                eyebrow="Step 4",
            ):
                pricing_cols = st.columns(2)
                admin_price = pricing_cols[0].number_input("Owner Price", min_value=0.0, step=1.0, key="create_admin_price")
                marketplace_price = pricing_cols[1].number_input("Marketplace Price", min_value=0.0, step=1.0, key="create_marketplace_price")
                manditrade_price = st.number_input("Mandiplace Price", min_value=0.0, step=1.0, key="create_manditrade_price")
                channel_cols = st.columns(2)
                marketplace_enabled = channel_cols[0].checkbox("Show in Marketplace", value=True, key="create_marketplace_enabled")
                manditrade_enabled = channel_cols[1].checkbox("Show in Mandiplace", value=True, key="create_manditrade_enabled")
                mandi_qty_cols = st.columns(2)
                manditrade_minimum_quantity = mandi_qty_cols[0].number_input("Mandiplace Minimum Quantity", min_value=1.0, step=1.0, value=1.0, key="create_manditrade_minimum_quantity")
                manditrade_increment_quantity = mandi_qty_cols[1].number_input("Mandiplace Quantity Step", min_value=1.0, step=1.0, value=1.0, key="create_manditrade_increment_quantity")

        with create_tabs[4]:
            with _render_onboarding_section(
                "Images and Approval",
                "Upload product images, finish consent checks, and choose the starting status for this product.",
                eyebrow="Step 5",
            ):
                uploaded_files = st.file_uploader(
                    "Product Images",
                    accept_multiple_files=True,
                    type=["png", "jpg", "jpeg", "webp"],
                    key="create_product_images",
                )
        owner_consent_record = {}
        delivery_partner_consent_record = {}
        with create_tabs[4]:
            with _render_onboarding_section(
                "Consent and Status",
                "Finish the required consent checks before saving the product.",
                eyebrow="Step 5",
            ):
                if is_admin and owner_email.strip():
                    owner_consent_record = _render_consent_panel(
                        product_consent_service=product_consent_service,
                        product_name=product_name,
                        recipient_email=owner_email,
                        requested_by=current_user_email,
                        consent_role="owner",
                        title="Owner Consent",
                        recipient_label="Owner",
                        session_prefix="create_owner_consent",
                    )
                if is_admin and delivery_partner_email.strip():
                    delivery_partner_consent_record = _render_consent_panel(
                        product_consent_service=product_consent_service,
                        product_name=product_name,
                        recipient_email=delivery_partner_email,
                        requested_by=current_user_email,
                        consent_role="delivery_partner",
                        title="Worker Consent",
                        recipient_label="Worker",
                        session_prefix="create_delivery_partner_consent",
                    )
                status = st.selectbox("Initial Status", options=["APPROVED", "PENDING_APPROVAL"] if is_admin else ["PENDING_APPROVAL"], index=0, key="create_status")
        submitted = st.button(translator.t("action.add_product"), use_container_width=True, key="save_product_button")

        if submitted:
            if not product_name.strip():
                st.error("Product name is required.")
                return
            owner_business_details_input = _normalize_owner_business_details(
                {
                    "business_name": owner_business_name,
                    "upi_id": owner_upi_id,
                    "gst_number": owner_gst_number,
                    "invoice_name": owner_invoice_name,
                    "invoice_address": owner_invoice_address,
                    "invoice_phone": owner_invoice_phone,
                    "bank_account_name": owner_bank_account_name,
                    "bank_account_number": owner_bank_account_number,
                    "bank_ifsc": owner_bank_ifsc,
                    "other_details": owner_other_details,
                }
            )
            missing_owner_fields = [
                label
                for field, label in (
                    ("business_name", "Owner Business Name"),
                    ("upi_id", "Owner UPI ID"),
                    ("gst_number", "Owner GST Number"),
                    ("invoice_name", "Invoice Name"),
                )
                if not owner_business_details_input.get(field)
            ]
            if missing_owner_fields:
                st.error(f"Owner details required during onboarding: {', '.join(missing_owner_fields)}.")
                return
            if is_admin and owner_email.strip():
                owner_consent_record = product_consent_service.get_consent_status(
                    product_name=product_name.strip(),
                    owner_email=owner_email,
                    requested_by=current_user_email,
                    consent_role="owner",
                )
                if str(owner_consent_record.get("status", "")).strip().upper() != "VERIFIED":
                    st.error("Owner consent OTP verification is required before product onboarding.")
                    return
            if is_admin and delivery_partner_email.strip():
                delivery_partner_consent_record = product_consent_service.get_consent_status(
                    product_name=product_name.strip(),
                    owner_email=delivery_partner_email,
                    requested_by=current_user_email,
                    consent_role="delivery_partner",
                )
                if str(delivery_partner_consent_record.get("status", "")).strip().upper() != "VERIFIED":
                    st.error("Worker consent OTP verification is required before product onboarding.")
                    return
            previous_users_snapshot = deepcopy(users)
            product_code = ""
            try:
                _validate_category_selection(category, subcategory, category_index)
                owner, owner_created = _resolve_or_create_owner(
                    users=users,
                    owner_email=owner_email,
                    owner_role=owner_role_key,
                    owner_display_name=owner_display_name,
                    owner_phone=owner_phone,
                    current_user_email=current_user_email,
                    data_service=data_service,
                    id_service=id_service,
                )
                owner_profile = owner_profile_service.save_owner_business_details(
                    actor_email=current_user_email,
                    actor_role=current_user_role,
                    target_email=owner_email,
                    role=owner_role_key,
                    display_name=owner.get("display_name", owner_email.split("@")[0]),
                    mobile=owner.get("phone", owner_phone.strip()),
                    business_details=owner_business_details_input,
                )
                owner_business_details = _normalize_owner_business_details(owner_profile.get("details", {}) or {})
                delivery_partner = {}
                if delivery_partner_email:
                    delivery_partner, _ = _resolve_or_create_owner(
                        users=users,
                        owner_email=delivery_partner_email,
                        owner_role="worker",
                        owner_display_name=delivery_partner_display_name,
                        owner_phone=delivery_partner_phone,
                        current_user_email=current_user_email,
                        data_service=data_service,
                        id_service=id_service,
                    )
                product_code = id_service.next_drive_id(data_service.admin_drive_service, "product", "PROD")
                uploaded_images = media_service.upload_product_images(
                    uploaded_files or [],
                    uploaded_by=current_user_email,
                    product_code=product_code,
                )
                for image in uploaded_images:
                    media_service.clear_cached_image(str(image.get("file_id", "")))
                record = {
                    "product_id": product_code,
                    "product_code": product_code,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                    "created_by": current_user_email,
                    "updated_by": current_user_email,
                }
                _apply_product_values(
                    product=record,
                    product_code=product_code,
                    owner=owner,
                    values={
                        "product_name": product_name.strip(),
                        "owner_email": owner_email,
                        "owner_phone": owner_phone.strip(),
                        "category": category,
                        "subcategory": subcategory,
                        "description": description.strip(),
                        "unit": unit.strip() or "piece",
                        "available_quantity": available_quantity,
                        "admin_price": admin_price,
                        "marketplace_enabled": marketplace_enabled,
                        "marketplace_price": marketplace_price,
                        "manditrade_enabled": manditrade_enabled,
                        "manditrade_price": manditrade_price,
                        "manditrade_minimum_quantity": manditrade_minimum_quantity,
                        "manditrade_increment_quantity": manditrade_increment_quantity,
                        "service_config": {
                            "packaging_mode": packaging_mode,
                            "shipping_mode": shipping_mode,
                            "delivery_scope": delivery_scope,
                            "packaging_cost_b2c": packaging_cost_b2c,
                            "shipping_cost_b2c": shipping_cost_b2c,
                            "packaging_cost_b2b": packaging_cost_b2b,
                            "shipping_cost_b2b": shipping_cost_b2b,
                            "delivery_notes": delivery_notes,
                        },
                        "status": status if is_admin else "PENDING_APPROVAL",
                        "delivery_partner": delivery_partner,
                        "managed_by_owner": shipment_management_mode == "Owner Managed",
                        "owner_business_details": owner_business_details,
                        "submitted_by": current_user_email,
                        "submitted_at": datetime.now(UTC).isoformat(),
                    },
                    current_user_email=current_user_email,
                    uploaded_images=uploaded_images,
                )
                if record["status"] == "APPROVED":
                    record["approval"]["approved_by"] = current_user_email
                    record["approval"]["approved_at"] = datetime.now(UTC).isoformat()
                if is_admin and owner_email.strip():
                    record["owner_consent"] = {
                        "status": str(owner_consent_record.get("status", "")).strip(),
                        "verified_at": str(owner_consent_record.get("verified_at", "")).strip(),
                        "requested_by": current_user_email,
                        "owner_email": owner_email,
                        "agreement_title": str(owner_consent_record.get("agreement_title", "")).strip(),
                        "agreement_body": str(owner_consent_record.get("agreement_body", "")).strip(),
                    }
                if is_admin and delivery_partner_email.strip():
                    record["delivery_partner_consent"] = {
                        "status": str(delivery_partner_consent_record.get("status", "")).strip(),
                        "verified_at": str(delivery_partner_consent_record.get("verified_at", "")).strip(),
                        "requested_by": current_user_email,
                        "delivery_partner_email": delivery_partner_email,
                        "agreement_title": str(delivery_partner_consent_record.get("agreement_title", "")).strip(),
                        "agreement_body": str(delivery_partner_consent_record.get("agreement_body", "")).strip(),
                    }
                products.append(record)
                _persist_products_and_users(data_service)
                notification_service.create_notification(
                    to_email=owner_email,
                    title="Product submitted",
                    message=f"{product_name} was submitted.",
                    event_type="PRODUCT_SUBMITTED",
                    to_role=owner_role_key,
                    owner_email=owner_email,
                    source_entity="products",
                    source_id=record["product_id"],
                    created_by=current_user_email,
                )
                if not is_admin:
                    notification_service.create_notification(
                        to_email="",
                        title="Product approval required",
                        message=f"{product_name} is awaiting approval.",
                        event_type="PRODUCT_SUBMITTED",
                        to_role="platform_admin",
                        owner_email=owner_email,
                        source_entity="products",
                        source_id=record["product_id"],
                        created_by=current_user_email,
                    )
                if owner_created:
                    notification_service.create_notification(
                        to_email=owner_email,
                        title="You have been onboarded to MandiTrade",
                        message=f"You have been onboarded as a {owner_role_key}.",
                        event_type="OWNER_ONBOARDED",
                        to_role=owner_role_key,
                        owner_email=owner_email,
                        source_entity="users",
                        source_id=owner.get("user_id", ""),
                        created_by=current_user_email,
                    )
                    notification_service.create_notification(
                        to_email=current_user_email,
                        title="New owner onboarded",
                        message=f"{owner_email} was onboarded as {owner_role_key}.",
                        event_type="OWNER_ONBOARDED",
                        to_role=current_user_role,
                        owner_email=owner_email,
                        source_entity="users",
                        source_id=owner.get("user_id", ""),
                        created_by=current_user_email,
                    )
                else:
                    notification_service.create_notification(
                        to_email=current_user_email,
                        title="Existing owner reused",
                        message=f"{owner_email} was reused for {product_name}.",
                        event_type="OWNER_REUSED",
                        to_role=current_user_role,
                        owner_email=owner_email,
                        source_entity="users",
                        source_id=owner.get("user_id", ""),
                        created_by=current_user_email,
                    )
                _persist_notifications(data_service)
                st.success(
                    "Product saved."
                    + (" Owner onboarded automatically." if owner_created else "")
                )
            except Exception as exc:
                users.clear()
                users.extend(previous_users_snapshot)
                if product_code:
                    products[:] = [product for product in products if product.get("product_id") != product_code]
                st.error(f"Drive write failed: {exc}")

    if is_admin:
        with tabs[7]:
            pending_products = [product for product in products if str(product.get("status", "")).upper() == "PENDING_APPROVAL"]
            render_table(_build_product_table_rows(pending_products), caption=translator.t("module.products.title"))
            selected_pending_id = st.selectbox(translator.t("action.approve"), options=[""] + [product.get("product_id", "") for product in pending_products], key="approve_product_id")
            selected_pending = next((product for product in pending_products if product.get("product_id") == selected_pending_id), None)
            if selected_pending:
                action = st.selectbox(translator.t("action.approve"), options=["APPROVE", "REJECT", "REQUEST_CHANGES", "ARCHIVE"], key="approval_action")
                rejection_reason = st.text_area(translator.t("field.description"), key="approval_reason")
                if st.button(translator.t("action.approve"), use_container_width=True, key="apply_approval_action"):
                    approval = dict(selected_pending.get("approval", {}) or {})
                    now = datetime.now(UTC).isoformat()
                    if action == "APPROVE":
                        selected_pending["status"] = "APPROVED"
                        approval["approved_by"] = current_user_email
                        approval["approved_at"] = now
                        notification_service.create_notification(
                            to_email=((selected_pending.get("owner") or {}).get("email", "")),
                            title="Product approved",
                            message=f"{selected_pending.get('product_name', 'Product')} was approved.",
                            event_type="PRODUCT_APPROVED",
                            to_role=((selected_pending.get("owner") or {}).get("role", "")),
                            owner_email=((selected_pending.get("owner") or {}).get("email", "")),
                            source_entity="products",
                            source_id=selected_pending.get("product_id", ""),
                            created_by=current_user_email,
                        )
                    elif action in {"REJECT", "REQUEST_CHANGES"}:
                        selected_pending["status"] = "REJECTED"
                        approval["rejected_by"] = current_user_email
                        approval["rejected_at"] = now
                        approval["rejection_reason"] = rejection_reason.strip() or ("Changes requested." if action == "REQUEST_CHANGES" else "")
                        notification_service.create_notification(
                            to_email=((selected_pending.get("owner") or {}).get("email", "")),
                            title="Product rejected" if action == "REJECT" else "Product changes requested",
                            message=f"{selected_pending.get('product_name', 'Product')} was rejected." if action == "REJECT" else f"Changes requested for {selected_pending.get('product_name', 'Product')}.",
                            event_type="PRODUCT_REJECTED" if action == "REJECT" else "PRODUCT_CHANGES_REQUESTED",
                            to_role=((selected_pending.get("owner") or {}).get("role", "")),
                            owner_email=((selected_pending.get("owner") or {}).get("email", "")),
                            source_entity="products",
                            source_id=selected_pending.get("product_id", ""),
                            created_by=current_user_email,
                        )
                    else:
                        selected_pending["status"] = "ARCHIVED"
                    selected_pending["approval"] = approval
                    selected_pending["updated_at"] = now
                    selected_pending["updated_by"] = current_user_email
                    data_service.persist_collection("products")
                    data_service.persist_collection("notifications")
                    data_service.persist_collection("gmail_queue")
                    st.success("Approval action applied.")
                    st.rerun()
