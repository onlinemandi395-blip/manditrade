from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import streamlit as st

from components.product_grid import render_product_grid
from components.table_renderer import render_table
from services.auth_service import is_bootstrap_admin
from services.id_service import IdService
from services.media_service import MediaService


OWNER_TYPES = {"Manufacturer": "manufacturer", "Mahajan": "mahajan"}
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
    rows = [
        user for user in users
        if str(user.get("role", "")).strip().lower() == normalized_role
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
    return "Manufacturer"


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


def _build_product_table_rows(products: list[dict]) -> list[dict]:
    rows = []
    for product in products:
        rows.append(
            {
                "product_code": product.get("product_code", ""),
                "product_name": product.get("product_name", ""),
                "owner_email": ((product.get("owner") or {}).get("email", "")),
                "owner_role": ((product.get("owner") or {}).get("role", "")),
                "category": product.get("category", ""),
                "subcategory": product.get("subcategory", ""),
                "admin_price": ((product.get("pricing") or {}).get("admin_price", 0)),
                "marketplace_price": ((product.get("pricing") or {}).get("marketplace_price", 0)),
                "manditrade_price": ((product.get("pricing") or {}).get("manditrade_price", 0)),
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
    product["sales_channels"] = {
        "marketplace": {"enabled": values["marketplace_enabled"]},
        "manditrade": {"enabled": values["manditrade_enabled"]},
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
    next_product_code = id_service.preview_drive_id(data_service.admin_drive_service, "product", "PROD")
    tab_labels = ["All Products", "Marketplace", "MandiTrade", "Pending Approval", "Approved", "Inactive/Archived", "Add Product"]
    if is_admin:
        tab_labels.append("Approve Products")
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_table(_build_product_table_rows(visible_products), caption="All products")
        active_product_ids = [product.get("product_id", "") for product in visible_products if str(product.get("status", "")).upper() != "ARCHIVED"]
        if active_product_ids:
            archive_product_id = st.selectbox(translator.t("action.archive"), options=[""] + active_product_ids, key="archive_product_id")
            if st.button(translator.t("action.archive"), use_container_width=True) and archive_product_id:
                _archive_product(products, archive_product_id, current_user_email)
                try:
                    data_service.persist_collection("products")
                    data_service.cache_service.refresh_cache()
                    st.success("Product archived.")
                except Exception as exc:
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
                else:
                    edit_role_key = current_user_role
                    edit_owner_email = str(current_user_email).strip().lower()
                    edit_owner_display_name = str(current_user_record.get("display_name", edit_owner_display_name)).strip()
                    edit_owner_phone = str(current_user_record.get("phone", edit_owner_phone)).strip()
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
                                "status": edit_status if is_admin else "PENDING_APPROVAL",
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
        st.caption(f"Product Code: {next_product_code}")
        product_name = st.text_input(translator.t("field.product_name"), key="create_product_name")
        if is_admin:
            owner_type = st.selectbox(translator.t("field.owner_type"), options=list(OWNER_TYPES.keys()), key="create_owner_type")
            owner_role_key = OWNER_TYPES[owner_type]
            owner_mode = st.radio("Owner Selection Mode", options=["Select Existing", "Add New"], horizontal=True, key="create_owner_mode")
            owner_candidates = _owner_candidates_for_role(users, products, owner_role_key)
            owner_email = ""
            owner_display_name = ""
            owner_phone = ""
            if owner_mode == "Select Existing" and owner_candidates:
                owner_option_map = {row.get("email", ""): row for row in owner_candidates}
                owner_choice = st.selectbox(
                    translator.t("field.owner_email"),
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
                    st.info("No existing active owners found for this role. Add a new owner.")
                owner_email = st.text_input(translator.t("field.owner_email"), key="create_owner_email").strip().lower()
                owner_display_name = st.text_input(translator.t("field.owner_display_name"), key="create_owner_display_name")
                owner_phone = st.text_input(translator.t("field.owner_phone"), key="create_owner_phone")
        else:
            owner_role_key = current_user_role
            owner_email = str(current_user_email).strip().lower()
            owner_display_name = str(current_user_record.get("display_name", "")).strip()
            owner_phone = str(current_user_record.get("phone", "")).strip()
            st.caption(f"Owner: {owner_email}")
            st.caption(f"Owner Role: {owner_role_key}")
        category = st.selectbox(translator.t("field.category"), options=category_names if category_names else [""], key="create_category")
        subcategories = category_index.get(category, [])
        subcategory = st.selectbox(translator.t("field.subcategory"), options=subcategories if subcategories else [""], key="create_subcategory")
        description = st.text_area(translator.t("field.description"), key="create_description")
        unit = st.text_input(translator.t("field.unit"), value="piece", key="create_unit")
        available_quantity = st.number_input(translator.t("field.quantity"), min_value=0.0, step=1.0, key="create_available_quantity")
        marketplace_enabled = st.checkbox(translator.t("field.available_marketplace"), value=True, key="create_marketplace_enabled")
        admin_price = st.number_input(translator.t("field.admin_price"), min_value=0.0, step=1.0, key="create_admin_price")
        marketplace_price = st.number_input(translator.t("field.marketplace_price"), min_value=0.0, step=1.0, key="create_marketplace_price")
        manditrade_enabled = st.checkbox(translator.t("field.available_manditrade"), value=True, key="create_manditrade_enabled")
        manditrade_price = st.number_input(translator.t("field.manditrade_price"), min_value=0.0, step=1.0, key="create_manditrade_price")
        uploaded_files = st.file_uploader(
            translator.t("field.product_images"),
            accept_multiple_files=True,
            type=["png", "jpg", "jpeg", "webp"],
            key="create_product_images",
        )
        status = st.selectbox(translator.t("field.status"), options=["APPROVED", "PENDING_APPROVAL"] if is_admin else ["PENDING_APPROVAL"], index=0, key="create_status")
        submitted = st.button(translator.t("action.add_product"), use_container_width=True, key="save_product_button")

        if submitted:
            if not product_name.strip():
                st.error("Product name is required.")
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
                        "status": status if is_admin else "PENDING_APPROVAL",
                        "submitted_by": current_user_email,
                        "submitted_at": datetime.now(UTC).isoformat(),
                    },
                    current_user_email=current_user_email,
                    uploaded_images=uploaded_images,
                )
                if record["status"] == "APPROVED":
                    record["approval"]["approved_by"] = current_user_email
                    record["approval"]["approved_at"] = datetime.now(UTC).isoformat()
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
