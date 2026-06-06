from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import streamlit as st

from components.product_grid import render_product_grid
from components.table_renderer import render_table


def _build_owner_index(users: list[dict]) -> dict[str, dict]:
    return {
        str(user.get("email", "")).strip().lower(): user
        for user in users
        if str(user.get("role", "")).strip().lower() in {"manufacturer", "mahajan"}
        and str(user.get("status", "ACTIVE")).upper() == "ACTIVE"
    }


def _archive_product(products: list[dict], product_id: str, current_user_email: str) -> None:
    for product in products:
        if product.get("product_id") == product_id:
            product["status"] = "ARCHIVED"
            product["updated_at"] = datetime.now(UTC).isoformat()
            product["updated_by"] = current_user_email
            return


def _update_product_record(product: dict, owner: dict, values: dict, current_user_email: str) -> None:
    product["product_code"] = values["product_code"]
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
    product["image_url"] = values["image_url"]
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


def render_products_page(data_service, notification_service, session_service, cache_service) -> None:
    products = data_service.get_collection_ref("products")
    users = data_service.list_collection("users")
    categories_config = cache_service.get_config("categories")
    category_rows = categories_config.get("categories", [])
    category_names = [row.get("category", "") for row in category_rows]
    owner_index = _build_owner_index(users)
    current_user_email = session_service.get_user().get("email", "")
    tabs = st.tabs(["All Products", "Marketplace", "MandiTrade", "Inactive", "Add Product"])

    with tabs[0]:
        render_table(
            [
                {
                    "image_url": product.get("image_url", ""),
                    "product_name": product.get("product_name", ""),
                    "product_code": product.get("product_code", ""),
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
                    st.success("Product archived.")
                except Exception as exc:
                    st.error(f"Drive write failed: {exc}")
        editable_ids = [product.get("product_id", "") for product in products]
        if editable_ids:
            selected_edit_id = st.selectbox("Edit Product", options=[""] + editable_ids, key="edit_product_id")
            selected_product = next((product for product in products if product.get("product_id") == selected_edit_id), None)
            if selected_product:
                with st.form("edit_product_form"):
                    edit_product_name = st.text_input("Product Name", value=selected_product.get("product_name", ""))
                    edit_product_code = st.text_input("Product Code", value=selected_product.get("product_code", ""))
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
                    edit_image_url = st.text_input("Image URL", value=selected_product.get("image_url", ""))
                    edit_unit = st.text_input("Unit", value=selected_product.get("unit", "piece"))
                    edit_available_quantity = st.number_input("Available Quantity", min_value=0.0, step=1.0, value=float((selected_product.get("inventory") or {}).get("available_quantity", 0)))
                    edit_marketplace_enabled = st.checkbox("Marketplace Enabled", value=((selected_product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled", False), key="edit_marketplace_enabled")
                    edit_marketplace_price = st.number_input("Marketplace Price", min_value=0.0, step=1.0, value=float(((selected_product.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0)))
                    edit_manditrade_enabled = st.checkbox("MandiTrade Enabled", value=((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled", False), key="edit_manditrade_enabled")
                    edit_manditrade_price = st.number_input("MandiTrade Price", min_value=0.0, step=1.0, value=float(((selected_product.get("sales_channels") or {}).get("manditrade") or {}).get("price", 0)))
                    edit_status = st.selectbox("Status", options=["ACTIVE", "INACTIVE", "ARCHIVED"], index=["ACTIVE", "INACTIVE", "ARCHIVED"].index(selected_product.get("status", "ACTIVE")) if selected_product.get("status", "ACTIVE") in ["ACTIVE", "INACTIVE", "ARCHIVED"] else 0, key="edit_status")
                    updated = st.form_submit_button("Update Product", use_container_width=True)
                if updated:
                    owner = owner_index.get(edit_owner_email)
                    if not owner:
                        st.error("Owner email must belong to an active Manufacturer or Mahajan.")
                        return
                    previous_snapshot = deepcopy(selected_product)
                    _update_product_record(
                        selected_product,
                        owner,
                        {
                            "product_name": edit_product_name.strip(),
                            "product_code": edit_product_code.strip(),
                            "owner_email": edit_owner_email,
                            "category": edit_category,
                            "subcategory": edit_subcategory,
                            "description": edit_description.strip(),
                            "image_url": edit_image_url.strip(),
                            "unit": edit_unit.strip() or "piece",
                            "available_quantity": edit_available_quantity,
                            "marketplace_enabled": edit_marketplace_enabled,
                            "marketplace_price": edit_marketplace_price,
                            "manditrade_enabled": edit_manditrade_enabled,
                            "manditrade_price": edit_manditrade_price,
                            "status": edit_status,
                        },
                        current_user_email,
                    )
                    try:
                        data_service.persist_collection("products")
                        st.success("Product updated.")
                    except Exception as exc:
                        selected_product.clear()
                        selected_product.update(previous_snapshot)
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
        with st.form("add_product_form"):
            product_name = st.text_input("Product Name")
            product_code = st.text_input("Product Code")
            owner_email = st.text_input("Owner Email").strip().lower()
            category = st.selectbox("Category", options=category_names if category_names else [""])
            subcategories = next((row.get("subcategories", []) for row in category_rows if row.get("category") == category), [])
            subcategory = st.selectbox("Subcategory", options=subcategories if subcategories else [""])
            description = st.text_area("Description")
            image_url = st.text_input("Image URL")
            unit = st.text_input("Unit", value="piece")
            available_quantity = st.number_input("Available Quantity", min_value=0.0, step=1.0)
            marketplace_enabled = st.checkbox("Marketplace Enabled", value=True)
            marketplace_price = st.number_input("Marketplace Price", min_value=0.0, step=1.0)
            manditrade_enabled = st.checkbox("MandiTrade Enabled", value=True)
            manditrade_price = st.number_input("MandiTrade Price", min_value=0.0, step=1.0)
            status = st.selectbox("Status", options=["ACTIVE", "INACTIVE", "ARCHIVED"], index=0)
            submitted = st.form_submit_button("Save Product", use_container_width=True)

        if submitted:
            owner = owner_index.get(owner_email)
            if not product_name.strip() or not product_code.strip():
                st.error("Product name and code are required.")
                return
            if not owner:
                st.error("Owner email must belong to an active Manufacturer or Mahajan.")
                return
            record = {
                "product_id": f"PROD_{len(products) + 1:03d}",
                "product_code": product_code.strip(),
                "product_name": product_name.strip(),
                "status": status,
                "owner": {
                    "email": owner_email,
                    "role": owner.get("role", ""),
                    "display_name": owner.get("display_name", owner_email.split("@")[0]),
                    "user_id": owner.get("user_id", ""),
                },
                "category": category,
                "subcategory": subcategory,
                "description": description.strip(),
                "image_url": image_url.strip(),
                "unit": unit.strip() or "piece",
                "sales_channels": {
                    "marketplace": {"enabled": marketplace_enabled, "price": marketplace_price},
                    "manditrade": {"enabled": manditrade_enabled, "price": manditrade_price},
                },
                "inventory": {
                    "available_quantity": available_quantity,
                    "manual_update_only": True,
                },
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "created_by": current_user_email,
                "updated_by": current_user_email,
            }
            products.append(record)
            try:
                data_service.persist_collection("products")
                notification_service.create_notification(
                    notification_type="PRODUCT_UPDATED",
                    title="Product created",
                    message=f"{product_name} was created.",
                    metadata={"to_email": owner_email, "product_id": record["product_id"]},
                )
                st.success("Product saved.")
            except Exception as exc:
                products.pop()
                st.error(f"Drive write failed: {exc}")
