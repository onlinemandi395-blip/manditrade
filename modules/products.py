from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from components.product_grid import render_product_grid
from components.table_renderer import render_table


def _build_user_index(users: list[dict], role: str) -> dict[str, dict]:
    return {
        str(user.get("email", "")).strip().lower(): user
        for user in users
        if str(user.get("role", "")).strip().lower() == role and str(user.get("status", "ACTIVE")).upper() == "ACTIVE"
    }


def render_products_page(data_service, notification_service, session_service) -> None:
    products = data_service.get_collection_ref("products")
    users = data_service.list_collection("users")
    manufacturer_index = _build_user_index(users, "manufacturer")
    mahajan_index = _build_user_index(users, "mahajan")
    tabs = st.tabs(["All Products", "Marketplace Products", "MandiTrade Products", "Draft / Inactive", "Add Product"])

    with tabs[0]:
        render_table(
            [
                {
                    "product_name": product.get("product_name", ""),
                    "category": product.get("category", ""),
                    "marketplace_price": ((product.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0),
                    "manditrade_price": ((product.get("sales_channels") or {}).get("manditrade") or {}).get("price", 0),
                    "manufacturer_email": ((product.get("manufacturer") or {}).get("email", "")),
                    "mahajan_email": ((product.get("mahajan") or {}).get("email", "")),
                    "inventory_quantity": ((product.get("inventory") or {}).get("available_quantity", 0)),
                    "status": product.get("status", "ACTIVE"),
                }
                for product in products
            ],
            caption="All products",
        )

    with tabs[1]:
        render_product_grid([product for product in products if ((product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled")], view="admin")

    with tabs[2]:
        render_product_grid([product for product in products if ((product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled")], view="admin")

    with tabs[3]:
        render_table(
            [product for product in products if str(product.get("status", "ACTIVE")).upper() != "ACTIVE"],
            caption="Draft or inactive products",
        )

    with tabs[4]:
        with st.form("add_product_form"):
            product_name = st.text_input("Product Name")
            product_code = st.text_input("Product Code")
            category = st.text_input("Category")
            subcategory = st.text_input("Subcategory")
            description = st.text_area("Description")
            unit = st.text_input("Unit", value="piece")
            image_url = st.text_input("Image URL")
            status = st.selectbox("Status", options=["ACTIVE", "INACTIVE", "DRAFT"], index=0)
            marketplace_enabled = st.checkbox("Marketplace Enabled", value=True)
            marketplace_price = st.number_input("Marketplace Price", min_value=0.0, step=1.0)
            manditrade_enabled = st.checkbox("MandiTrade Enabled", value=True)
            manditrade_price = st.number_input("MandiTrade Price", min_value=0.0, step=1.0)
            available_quantity = st.number_input("Available Quantity", min_value=0.0, step=1.0)
            manufacturer_email = st.selectbox("Manufacturer Email", options=[""] + sorted(manufacturer_index.keys()))
            mahajan_email = st.selectbox("Mahajan Email", options=[""] + sorted(mahajan_index.keys()))
            submitted = st.form_submit_button("Save Product", use_container_width=True)
        if submitted:
            if not product_name.strip() or not product_code.strip():
                st.error("Product name and code are required.")
            else:
                if not manufacturer_email or manufacturer_email not in manufacturer_index:
                    st.error("Manufacturer email not found or inactive.")
                    return
                if not mahajan_email or mahajan_email not in mahajan_index:
                    st.error("Mahajan email not found or inactive.")
                    return
                manufacturer_user = manufacturer_index[manufacturer_email]
                mahajan_user = mahajan_index[mahajan_email]
                record = {
                    "product_id": f"PROD_{len(products) + 1:03d}",
                    "product_code": product_code.strip(),
                    "product_name": product_name.strip(),
                    "status": status,
                    "category": category.strip() or "General",
                    "subcategory": subcategory.strip(),
                    "description": description.strip(),
                    "image_url": image_url.strip(),
                    "unit": unit.strip() or "piece",
                    "sales_channels": {
                        "marketplace": {"enabled": marketplace_enabled, "price": marketplace_price},
                        "manditrade": {"enabled": manditrade_enabled, "price": manditrade_price},
                    },
                    "manufacturer": {
                        "email": manufacturer_email,
                        "manufacturer_id": str(manufacturer_user.get("user_id", "") or manufacturer_user.get("id", "") or "MFG_001"),
                        "name": manufacturer_user.get("display_name", manufacturer_email.split("@")[0]),
                        "phone": manufacturer_user.get("phone", ""),
                        "active": True,
                    },
                    "mahajan": {
                        "email": mahajan_email,
                        "mahajan_id": str(mahajan_user.get("user_id", "") or mahajan_user.get("id", "") or "MHJ_001"),
                        "name": mahajan_user.get("display_name", mahajan_email.split("@")[0]),
                        "phone": mahajan_user.get("phone", ""),
                        "active": True,
                    },
                    "inventory": {
                        "available_quantity": available_quantity,
                        "unit": unit.strip() or "piece",
                        "manual_update_only": True,
                    },
                    "routing": {
                        "marketplace_orders": {
                            "route_to": "manufacturer",
                            "notify": ["platform_admin", "manufacturer"],
                        },
                        "manditrade_orders": {
                            "route_to": "platform_admin",
                            "assigned_supplier": "manufacturer",
                            "notify": ["platform_admin", "manufacturer", "mahajan"],
                        },
                    },
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                products.append(record)
                notification_service.create_notification(
                    notification_type="PRODUCT_UPDATED",
                    title="Product mapped to manufacturer",
                    message=f"{product_name} was mapped to your manufacturer account.",
                    metadata={"to_email": manufacturer_email, "product_id": record["product_id"]},
                )
                notification_service.create_notification(
                    notification_type="PRODUCT_UPDATED",
                    title="Product mapped to mahajan",
                    message=f"{product_name} was mapped to your mahajan account.",
                    metadata={"to_email": mahajan_email, "product_id": record["product_id"]},
                )
                notification_service.create_notification(
                    notification_type="PRODUCT_UPDATED",
                    title="Product created",
                    message=f"{product_name} was created.",
                    metadata={"to_email": session_service.get_user().get("email", ""), "product_id": record["product_id"]},
                )
                st.success("Product saved.")
