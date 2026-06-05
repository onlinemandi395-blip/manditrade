from __future__ import annotations

from html import escape

import streamlit as st

from components.data_grid import render_data_grid
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.filter_bar import render_filter_bar
from components.html_renderer import render_html
from components.paginated_table import render_paginated_table
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from components.ui_shell import render_dual_panel, render_mobile_record_card, render_showcase_strip
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state, render_metric_button_row


def render_products_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    product_catalog_service = app_context["product_catalog_service"]
    viewer_role = user.role if user else None
    viewer_code = user.manufacturer_code if user else None
    products = product_catalog_service.list_products(
        include_pending=bool(viewer_role == "platform_admin"),
        viewer_role=viewer_role,
        viewer_code=viewer_code,
    )
    image_service = app_context.get("image_service")
    inventory_service = app_context.get("inventory_service")
    render_platform_shell(
        title="Products",
        subtitle="Govern finished products for catalog selling, approvals, and pricing. Raw-material supply belongs on the Raw Materials and Mandi Orders pages.",
        badges=["Public Catalog", "Mandi Price", "Three-Tier Pricing"],
        role=viewer_role.replace("_", " ").title() if viewer_role else "Catalog View",
        metrics=[("Catalog Mode", "Governed visibility"), ("Proposal Path", "Manufacturer to admin")],
        kicker="Digital Manpur Catalog Grid",
        breadcrumbs=["Workspace", "Catalog", "Products"],
        primary_actions=["Propose Product" if viewer_role in {"manufacturer", "admin_as_manufacturer"} else "Manage Catalog"],
    )
    render_kpi_cards(
        [
            {"label": "Catalog Products", "value": str(len(products)), "status": "SUCCESS"},
            {"label": "Proposed", "value": str(len([item for item in products if item.get("status") == "PROPOSED"])), "status": "PENDING"},
            {"label": "Active", "value": str(len([item for item in products if item.get("status") == "ACTIVE"])), "status": "OPEN"},
        ]
    )
    render_metric_button_row(
        "products",
        [
            {"label": "Overview", "value": str(len(products)), "tab_name": "Overview"},
            {"label": "Registry", "value": str(len(products)), "tab_name": "Overview"},
            {"label": "Create", "value": str(len([item for item in products if item.get('status') == 'PROPOSED'])), "tab_name": "Activity"},
            {"label": "Activity", "value": str(len([item for item in products if item.get('status') == 'ACTIVE'])), "tab_name": "Proposal Threads"},
        ],
    )
    render_showcase_strip(
        [
            ("Public Catalog", str(len(products)), "SUCCESS"),
            ("Proposed", str(len([item for item in products if item.get('status') == 'PROPOSED'])), "PENDING"),
            ("Visible Active", str(len([item for item in products if item.get('status') == 'ACTIVE'])), "OPEN"),
        ]
    )
    render_dual_panel(
        "Pricing Governance",
        render_mobile_record_card({"Mandi Price": "Manufacturer B2B", "Marketplace Price": "Public buyer", "Supply Price": "Raw material lane"}),
        "Onboarding Flow",
        render_mobile_record_card({"Propose": "Manufacturer/Admin", "Approve": "Platform Admin"}),
    )
    overview_tab, activity_tab, thread_tab = st.tabs(["Overview", "Activity", "Proposal Threads"])
    with overview_tab:
        render_section_intro("Finished Product Catalog", "Manufacturers can propose finished products here. Raw materials and supplier quotes stay in the admin-managed supply workflow.")
        preview_products = products[:3]
        if preview_products:
            card_columns = st.columns(min(len(preview_products), 3))
            for index, item in enumerate(preview_products):
                with card_columns[index % len(card_columns)]:
                    image = image_service.get_display_image(item, label=str(item.get("name", "Product"))) if image_service else {"src": "", "alt": str(item.get("name", "Product")), "status": "NONE"}
                    render_product_card(
                        item=item,
                        variant="MARKETPLACE_PRODUCT",
                        image=image,
                        title=str(item.get("name", item.get("product_id", "Product"))),
                        subtitle=str(item.get("category", "General")),
                        price_label="Marketplace",
                        price_value=str(item.get("approved_marketplace_price", item.get("suggested_marketplace_price", item.get("marketplace_price", item.get("mrp", 0))))),
                        availability_label=(
                            f"{inventory_service.stock_status(inventory_service.get_marketplace_inventory_for_product(item)).replace('_', ' ').title()} | "
                            f"Qty {int((inventory_service.get_marketplace_inventory_for_product(item) or {}).get('available_qty', 0) or 0)}"
                            if inventory_service
                            else str(item.get("status", "ACTIVE"))
                        ),
                        visibility_label=str(item.get("approved_visibility", item.get("visibility_request", "MANDI_NETWORK"))),
                        action_label="View Product",
                        action_key=f"products_preview_{item.get('product_id', index)}",
                    )
        filtered_products = render_data_grid(page_key="products_catalog", rows=products, search_fields=["product_id", "name", "category", "created_by_manufacturer_id"], status_field="status", date_field="updated_at", price_field="approved_marketplace_price", search_placeholder="Search by product ID or name")
        if filtered_products:
            pass
        else:
            render_empty_state("No finished products are visible for this view yet.")
    if not user:
        return
    if user.role == "platform_admin":
        with activity_tab:
            st.markdown("### Manage Approved Products")
            approved_products = [item for item in products if item.get("status") == "ACTIVE"]
            if not approved_products:
                st.info("No approved products are available for admin updates yet.")
            else:
                selected_id = st.selectbox("Select Approved Product", [item["product_id"] for item in approved_products])
                selected = next(item for item in approved_products if item["product_id"] == selected_id)
                with st.form("admin_update_product"):
                    col1, col2 = st.columns(2)
                    updated_name = col1.text_input("Product Name", value=selected.get("name", ""))
                    updated_category = col2.text_input("Category", value=selected.get("category", ""))
                    updated_unit = col1.text_input("Unit", value=selected.get("unit", "kg"))
                    updated_description = st.text_area("Description", value=selected.get("description", ""), height=100)
                    approved_mandi_price = col1.number_input("Approved Mandi Price", min_value=0.0, step=1.0, value=float(selected.get("approved_mandi_price", selected.get("mandi_price", 0)) or 0))
                    approved_client_price = col2.number_input("Approved B2B Price", min_value=0.0, step=1.0, value=float(selected.get("approved_client_price", selected.get("client_price", selected.get("mrp", 0))) or 0))
                    approved_marketplace_price = col1.number_input("Approved Marketplace Price", min_value=0.0, step=1.0, value=float(selected.get("approved_marketplace_price", selected.get("marketplace_price", selected.get("mrp", 0))) or 0))
                    visibility_request = col1.selectbox("Visibility Request", ["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"], index=["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"].index(selected.get("visibility_request", "MANDI_NETWORK")) if selected.get("visibility_request", "MANDI_NETWORK") in {"PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"} else 2)
                    approved_visibility = col2.selectbox("Approved Visibility", ["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"], index=["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"].index(selected.get("approved_visibility", "PUBLIC")) if selected.get("approved_visibility", "PUBLIC") in {"PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"} else 0)
                    minimum_order_qty = col1.number_input("Minimum Order Quantity", min_value=1, step=1, value=int(selected.get("minimum_order_qty", 1) or 1))
                    available_for_public_sale = col1.checkbox("Available For Public Sale?", value=bool(selected.get("available_for_public_sale", False)))
                    available_for_mandi_network = col2.checkbox("Available For Mandi Network?", value=bool(selected.get("available_for_mandi_network", True)))
                    public_seller_manufacturer_id = col2.text_input("Public Seller Manufacturer ID", value=selected.get("public_seller_manufacturer_id", selected.get("created_by_manufacturer_id", "")))
                    visible = col1.checkbox("Visible to Active Catalog?", value=bool(selected.get("visible", True)))
                    image_url = st.text_input("Product Image URL", value=selected.get("image_url", ""))
                    image_alt_text = st.text_input("Image Alt Text", value=selected.get("image_alt_text", selected.get("name", "")))
                    uploaded_image = st.file_uploader("Optional Product Image Upload", type=["jpg", "jpeg", "png"], key=f"product_upload_{selected_id}")
                    admin_note = st.text_area("Admin Note", value=selected.get("admin_note", ""), height=100)
                    update_submit = st.form_submit_button("Save Product Updates")
                if update_submit:
                    image_file_ref = image_service.save_uploaded_image_if_supported(uploaded_image, folder="products") if image_service and uploaded_image else selected.get("image_file_ref", "")
                    product_catalog_service.update_product(
                        product_id=selected_id,
                        updated_by="PLATFORM_ADMIN",
                        updates={
                            "name": updated_name,
                            "category": updated_category,
                            "unit": updated_unit,
                            "description": updated_description,
                            "approved_mandi_price": approved_mandi_price,
                            "approved_client_price": approved_client_price,
                            "approved_marketplace_price": approved_marketplace_price,
                            "visibility_request": visibility_request,
                            "approved_visibility": approved_visibility,
                            "minimum_order_qty": minimum_order_qty,
                            "available_for_public_sale": available_for_public_sale,
                            "available_for_mandi_network": available_for_mandi_network,
                            "public_seller_manufacturer_id": public_seller_manufacturer_id,
                            "visible": visible,
                            "image_url": image_url,
                            "image_file_ref": image_file_ref,
                            "image_alt_text": image_alt_text,
                            "admin_note": admin_note,
                        },
                    )
                    st.success("Approved product updated.")
                    st.rerun()
                if st.button("Archive Selected Product", use_container_width=True):
                    product_catalog_service.delete_product(product_id=selected_id)
                    st.warning(f"{selected_id} archived from catalog.")
                    st.rerun()
        return
    if user.role not in {"manufacturer", "admin_as_manufacturer"}:
        return

    with activity_tab:
        with st.form("propose_product"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Product Name")
            category = col2.text_input("Category")
            unit = col1.text_input("Unit", value="kg")
            description = st.text_area("Description", height=100)
            suggested_mandi_price = col1.number_input("Suggested Mandi Price", min_value=0.0, step=1.0)
            suggested_client_price = col2.number_input("Suggested B2B Price", min_value=0.0, step=1.0)
            suggested_marketplace_price = col1.number_input("Suggested Marketplace Price", min_value=0.0, step=1.0)
            visibility_request = col1.selectbox("Product Visibility Request", ["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"], index=2)
            minimum_order_qty = col2.number_input("Minimum Order Quantity", min_value=1, step=1, value=1)
            available_for_public_sale = col1.checkbox("Available For Public Sale?")
            available_for_mandi_network = col2.checkbox("Available For Mandi Network?", value=True)
            image_url = st.text_input("Product Image URL", placeholder="Optional image URL")
            image_alt_text = st.text_input("Image Alt Text", placeholder="Short image description")
            uploaded_image = st.file_uploader("Optional Product Image Upload", type=["jpg", "jpeg", "png"], key="propose_product_upload")
            submitted = st.form_submit_button("Propose Product")
        if submitted and name and category and unit:
            created_by = user.manufacturer_code or ""
            image_file_ref = image_service.save_uploaded_image_if_supported(uploaded_image, folder="products") if image_service and uploaded_image else ""
            app_context["product_catalog_service"].propose_product(
                created_by=created_by,
                created_by_email=user.email,
                name=name,
                category=category,
                unit=unit,
                description=description,
                suggested_mandi_price=suggested_mandi_price,
                suggested_client_price=suggested_client_price,
                suggested_marketplace_price=suggested_marketplace_price,
                visibility_request=visibility_request,
                minimum_order_qty=minimum_order_qty,
                available_for_public_sale=available_for_public_sale,
                available_for_mandi_network=available_for_mandi_network,
                image_url=image_url,
                image_file_ref=image_file_ref,
                image_alt_text=image_alt_text,
            )
            st.success("Product proposal saved with PROPOSED status.")
            st.rerun()

    own_proposals = [
        item
        for item in products
        if item.get("status") == "PROPOSED"
        and (item.get("created_by_manufacturer_id") == viewer_code or item.get("created_by") == viewer_code)
    ]
    with thread_tab:
        if not own_proposals:
            render_empty_state("No proposed products need your follow-up right now.")
            return

        st.markdown("### My Proposed Products")
        for proposal in own_proposals:
            label = f"{proposal.get('name', proposal.get('product_id'))} ({proposal.get('clarification_status', 'NONE')})"
            with st.expander(label):
                st.json(
                    {
                        "status": proposal.get("status", "PROPOSED"),
                        "clarification_status": proposal.get("clarification_status", "NONE"),
                        "suggested_mandi_price": proposal.get("suggested_mandi_price", 0),
                        "suggested_client_price": proposal.get("suggested_client_price", proposal.get("suggested_mrp", 0)),
                        "suggested_marketplace_price": proposal.get("suggested_marketplace_price", proposal.get("suggested_mrp", 0)),
                        "visibility_request": proposal.get("visibility_request", "MANDI_NETWORK"),
                        "minimum_order_qty": proposal.get("minimum_order_qty", 1),
                    },
                    expanded=False,
                )
                comments = product_catalog_service.list_product_comments(proposal["product_id"], user)
                if comments:
                    st.dataframe(comments, use_container_width=True)
                else:
                    st.info("No admin comments on this proposal yet.")
                with st.form(f"manufacturer_reply_{proposal['product_id']}"):
                    reply = st.text_area("Reply to Platform Admin", height=100)
                    reply_submit = st.form_submit_button("Send Reply")
                if reply_submit and reply.strip():
                    product_catalog_service.add_product_comment(proposal["product_id"], user, reply)
                    st.success("Reply added to proposal thread.")
                    st.rerun()
