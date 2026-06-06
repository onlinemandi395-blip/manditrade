from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import streamlit as st

from components.product_grid import render_product_grid
from components.table_renderer import render_table
from services.id_service import IdService
from services.media_service import MediaService


OWNER_TYPES = {"Manufacturer": "manufacturer", "Mahajan": "mahajan"}
STATUSES = ["ACTIVE", "INACTIVE", "ARCHIVED"]


def _build_user_index(users: list[dict]) -> dict[str, dict]:
    return {str(user.get("email", "")).strip().lower(): user for user in users if str(user.get("email", "")).strip()}


def _get_owner_type_label(product: dict) -> str:
    owner_role = str(((product.get("owner") or {}).get("role", ""))).strip().lower()
    for label, value in OWNER_TYPES.items():
        if value == owner_role:
            return label
    return "Manufacturer"


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
        if str(existing.get("status", "ACTIVE")).upper() != "ACTIVE":
            raise ValueError("Owner email exists but is not ACTIVE.")
        return existing, False
    user_id = id_service.next_drive_id(data_service.admin_drive_service, "user", "USR")
    new_user = {
        "user_id": user_id,
        "email": normalized_email,
        "role": owner_role,
        "status": "ACTIVE",
        "display_name": "",
        "source": "product_onboarding",
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": current_user_email,
    }
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
    product["sales_channels"] = {
        "marketplace": {"enabled": values["marketplace_enabled"], "price": values["marketplace_price"]},
        "manditrade": {"enabled": values["manditrade_enabled"], "price": values["manditrade_price"]},
    }
    product["inventory"] = {
        "available_quantity": values["available_quantity"],
        "manual_update_only": True,
    }
    product["updated_at"] = datetime.now(UTC).isoformat()
    product["updated_by"] = current_user_email


def _persist_products_and_users(data_service) -> None:
    data_service.persist_collection("users")
    data_service.persist_collection("products")


def render_products_page(data_service, notification_service, session_service, cache_service) -> None:
    products = data_service.get_collection_ref("products")
    users = data_service.get_collection_ref("users")
    categories_config = cache_service.get_config("categories")
    category_rows = categories_config.get("categories", [])
    category_names = [row.get("category", "") for row in category_rows]
    current_user_email = session_service.get_user().get("email", "")
    id_service = IdService()
    media_service = MediaService(data_service.admin_drive_service)
    next_product_code = id_service.preview_drive_id(data_service.admin_drive_service, "product", "PROD")
    tabs = st.tabs(["All Products", "Marketplace", "MandiTrade", "Inactive", "Add Product"])

    with tabs[0]:
        render_table(
            [
                {
                    "image_url": product.get("image_url", ""),
                    "product_code": product.get("product_code", ""),
                    "product_name": product.get("product_name", ""),
                    "owner_email": ((product.get("owner") or {}).get("email", "")),
                    "owner_role": ((product.get("owner") or {}).get("role", "")),
                    "category": product.get("category", ""),
                    "subcategory": product.get("subcategory", ""),
                    "marketplace_price": ((product.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0),
                    "manditrade_price": ((product.get("sales_channels") or {}).get("manditrade") or {}).get("price", 0),
                    "quantity": ((product.get("inventory") or {}).get("available_quantity", 0)),
                    "status": product.get("status", "ACTIVE"),
                }
                for product in products
            ],
            caption="All products",
        )
        active_product_ids = [product.get("product_id", "") for product in products if str(product.get("status", "")).upper() != "ARCHIVED"]
        if active_product_ids:
            archive_product_id = st.selectbox("Archive Product", options=[""] + active_product_ids, key="archive_product_id")
            if st.button("Archive Selected Product", use_container_width=True) and archive_product_id:
                _archive_product(products, archive_product_id, current_user_email)
                try:
                    data_service.persist_collection("products")
                    data_service.cache_service.refresh_cache()
                    st.success("Product archived.")
                except Exception as exc:
                    st.error(f"Drive write failed: {exc}")
        editable_ids = [product.get("product_id", "") for product in products]
        if editable_ids:
            selected_edit_id = st.selectbox("Edit Product", options=[""] + editable_ids, key="edit_product_id")
            selected_product = next((product for product in products if product.get("product_id") == selected_edit_id), None)
            if selected_product:
                existing_images = selected_product.get("images", []) or []
                st.caption(f"Product Code: {selected_product.get('product_code', '')}")
                if existing_images:
                    st.image(
                        [image.get("image_url") or image.get("thumbnail_link") or image.get("web_view_link") for image in existing_images if image.get("image_url") or image.get("thumbnail_link") or image.get("web_view_link")],
                        width=120,
                    )
                with st.form("edit_product_form"):
                    edit_product_name = st.text_input("Product Name", value=selected_product.get("product_name", ""))
                    edit_owner_type = st.selectbox(
                        "Owner Type",
                        options=list(OWNER_TYPES.keys()),
                        index=list(OWNER_TYPES.keys()).index(_get_owner_type_label(selected_product)),
                    )
                    edit_owner_email = st.text_input("Owner Email", value=((selected_product.get("owner") or {}).get("email", ""))).strip().lower()
                    edit_category = st.selectbox(
                        "Category",
                        options=category_names if category_names else [""],
                        index=category_names.index(selected_product.get("category", "")) if selected_product.get("category", "") in category_names else 0,
                        key="edit_category",
                    )
                    edit_subcategories = next((row.get("subcategories", []) for row in category_rows if row.get("category") == edit_category), [])
                    edit_subcategory = st.selectbox(
                        "Subcategory",
                        options=edit_subcategories if edit_subcategories else [""],
                        index=edit_subcategories.index(selected_product.get("subcategory", "")) if selected_product.get("subcategory", "") in edit_subcategories else 0,
                        key="edit_subcategory",
                    )
                    edit_description = st.text_area("Description", value=selected_product.get("description", ""))
                    edit_unit = st.text_input("Unit", value=selected_product.get("unit", "piece"))
                    edit_available_quantity = st.number_input("Available Quantity", min_value=0.0, step=1.0, value=float((selected_product.get("inventory") or {}).get("available_quantity", 0)))
                    edit_marketplace_enabled = st.checkbox("Marketplace Enabled", value=((selected_product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled", False), key="edit_marketplace_enabled")
                    edit_marketplace_price = st.number_input("Marketplace Price", min_value=0.0, step=1.0, value=float(((selected_product.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0)))
                    edit_manditrade_enabled = st.checkbox("MandiTrade Enabled", value=((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled", False), key="edit_manditrade_enabled")
                    edit_manditrade_price = st.number_input("MandiTrade Price", min_value=0.0, step=1.0, value=float(((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("price", 0)))
                    edit_status = st.selectbox("Status", options=STATUSES, index=STATUSES.index(selected_product.get("status", "ACTIVE")) if selected_product.get("status", "ACTIVE") in STATUSES else 0)
                    edit_uploaded_files = st.file_uploader(
                        "Product Images Upload",
                        accept_multiple_files=True,
                        type=["png", "jpg", "jpeg", "webp"],
                        key="edit_product_images",
                    )
                    updated = st.form_submit_button("Update Product", use_container_width=True)
                if updated:
                    if not edit_product_name.strip():
                        st.error("Product name is required.")
                        return
                    previous_product_snapshot = deepcopy(selected_product)
                    previous_users_snapshot = deepcopy(users)
                    try:
                        owner, _ = _resolve_or_create_owner(
                            users=users,
                            owner_email=edit_owner_email,
                            owner_role=OWNER_TYPES[edit_owner_type],
                            current_user_email=current_user_email,
                            data_service=data_service,
                            id_service=id_service,
                        )
                        uploaded_images = existing_images
                        if edit_uploaded_files:
                            uploaded_images = media_service.upload_product_images(edit_uploaded_files, uploaded_by=current_user_email)
                        _apply_product_values(
                            product=selected_product,
                            product_code=selected_product.get("product_code", selected_product.get("product_id", "")),
                            owner=owner,
                            values={
                                "product_name": edit_product_name.strip(),
                                "owner_email": edit_owner_email,
                                "category": edit_category,
                                "subcategory": edit_subcategory,
                                "description": edit_description.strip(),
                                "unit": edit_unit.strip() or "piece",
                                "available_quantity": edit_available_quantity,
                                "marketplace_enabled": edit_marketplace_enabled,
                                "marketplace_price": edit_marketplace_price,
                                "manditrade_enabled": edit_manditrade_enabled,
                                "manditrade_price": edit_manditrade_price,
                                "status": edit_status,
                            },
                            current_user_email=current_user_email,
                            uploaded_images=uploaded_images,
                        )
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
                for product in products
                if ((product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled")
                and str(product.get("status", "ACTIVE")).upper() == "ACTIVE"
            ],
            view="admin",
        )

    with tabs[2]:
        render_product_grid(
            [
                product
                for product in products
                if ((product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled")
                and str(product.get("status", "ACTIVE")).upper() == "ACTIVE"
            ],
            view="admin",
        )

    with tabs[3]:
        render_table(
            [product for product in products if str(product.get("status", "ACTIVE")).upper() != "ACTIVE"],
            caption="Inactive / archived products",
        )

    with tabs[4]:
        st.caption(f"Product Code: {next_product_code}")
        with st.form("add_product_form"):
            product_name = st.text_input("Product Name")
            owner_type = st.selectbox("Owner Type", options=list(OWNER_TYPES.keys()))
            owner_email = st.text_input("Owner Email").strip().lower()
            category = st.selectbox("Category", options=category_names if category_names else [""])
            subcategories = next((row.get("subcategories", []) for row in category_rows if row.get("category") == category), [])
            subcategory = st.selectbox("Subcategory", options=subcategories if subcategories else [""])
            description = st.text_area("Description")
            unit = st.text_input("Unit", value="piece")
            available_quantity = st.number_input("Available Quantity", min_value=0.0, step=1.0)
            marketplace_enabled = st.checkbox("Marketplace Enabled", value=True)
            marketplace_price = st.number_input("Marketplace Price", min_value=0.0, step=1.0)
            manditrade_enabled = st.checkbox("MandiTrade Enabled", value=True)
            manditrade_price = st.number_input("MandiTrade Price", min_value=0.0, step=1.0)
            uploaded_files = st.file_uploader(
                "Product Images Upload",
                accept_multiple_files=True,
                type=["png", "jpg", "jpeg", "webp"],
                key="create_product_images",
            )
            status = st.selectbox("Status", options=STATUSES, index=0)
            submitted = st.form_submit_button("Save Product", use_container_width=True)

        if submitted:
            if not product_name.strip():
                st.error("Product name is required.")
                return
            previous_users_snapshot = deepcopy(users)
            product_code = ""
            try:
                owner, owner_created = _resolve_or_create_owner(
                    users=users,
                    owner_email=owner_email,
                    owner_role=OWNER_TYPES[owner_type],
                    current_user_email=current_user_email,
                    data_service=data_service,
                    id_service=id_service,
                )
                product_code = id_service.next_drive_id(data_service.admin_drive_service, "product", "PROD")
                uploaded_images = media_service.upload_product_images(uploaded_files or [], uploaded_by=current_user_email)
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
                        "category": category,
                        "subcategory": subcategory,
                        "description": description.strip(),
                        "unit": unit.strip() or "piece",
                        "available_quantity": available_quantity,
                        "marketplace_enabled": marketplace_enabled,
                        "marketplace_price": marketplace_price,
                        "manditrade_enabled": manditrade_enabled,
                        "manditrade_price": manditrade_price,
                        "status": status,
                    },
                    current_user_email=current_user_email,
                    uploaded_images=uploaded_images,
                )
                products.append(record)
                _persist_products_and_users(data_service)
                notification_service.create_notification(
                    notification_type="PRODUCT_UPDATED",
                    title="Product created",
                    message=f"{product_name} was created.",
                    metadata={"to_email": owner_email, "product_id": record["product_id"]},
                )
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
