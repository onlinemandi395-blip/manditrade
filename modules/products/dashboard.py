from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip


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
    render_page_header(
        "Products",
        "Govern public mandi catalog, approvals, and pricing without slipping back into ERP complexity.",
        ["Public Catalog", "Mandi Price", "MRP"],
        role=viewer_role.replace("_", " ").title() if viewer_role else "Catalog View",
        metrics=[("Catalog Mode", "Governed visibility"), ("Proposal Path", "Manufacturer to admin")],
        kicker="Digital Manpur Catalog Grid",
    )
    render_metric_grid(
        [
            render_metric_card("Catalog Products", str(len(products)), "SUCCESS"),
            render_metric_card("Proposed", str(len([item for item in products if item.get("status") == "PROPOSED"])), "PENDING"),
            render_metric_card("Active", str(len([item for item in products if item.get("status") == "ACTIVE"])), "OPEN"),
        ]
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
        render_mobile_record_card({"Mandi Price": "Admin-governed", "MRP": "Public-facing"}),
        "Onboarding Flow",
        render_mobile_record_card({"Propose": "Manufacturer/Admin", "Approve": "Platform Admin"}),
    )
    product_preview = "".join(
        f"""
        <article class="mt-product-card">
          <div class="mt-product-card__image"></div>
          <h3>{escape(str(item.get('name', item.get('product_id', 'Product'))))}</h3>
          <p>{escape(str(item.get('description', 'Governed catalog product with pricing and visibility controls.') or 'Governed catalog product with pricing and visibility controls.'))}</p>
          <div class="mt-chip-row">
            <span class="mt-price-chip">Mandi: {escape(str(item.get('approved_mandi_price', item.get('suggested_mandi_price', item.get('mandi_price', 0)))))}</span>
            <span class="mt-price-chip">MRP: {escape(str(item.get('approved_mrp', item.get('suggested_mrp', item.get('mrp', 0)))))}</span>
          </div>
          <div class="mt-chip-row">
            <span class="mt-chip">{escape(str(item.get('approved_visibility', item.get('visibility_request', 'MANDI_NETWORK'))))}</span>
            <span class="mt-chip">{escape(str(item.get('status', 'ACTIVE')))}</span>
          </div>
        </article>
        """
        for item in products[:3]
    )
    overview_tab, activity_tab, thread_tab = st.tabs(["Overview", "Activity", "Proposal Threads"])
    with overview_tab:
        render_section_intro("Catalog Governance", "Manufacturers can propose products and platform admin approves them with mandi price and MRP.")
        if product_preview:
            render_html(f"<section class='mt-grid mt-grid--actions'>{product_preview}</section>")
        st.dataframe(products, use_container_width=True)
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
                    approved_mrp = col2.number_input("Approved MRP", min_value=0.0, step=1.0, value=float(selected.get("approved_mrp", selected.get("mrp", 0)) or 0))
                    visibility_request = col1.selectbox("Visibility Request", ["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"], index=["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"].index(selected.get("visibility_request", "MANDI_NETWORK")) if selected.get("visibility_request", "MANDI_NETWORK") in {"PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"} else 2)
                    approved_visibility = col2.selectbox("Approved Visibility", ["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"], index=["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"].index(selected.get("approved_visibility", "PUBLIC")) if selected.get("approved_visibility", "PUBLIC") in {"PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"} else 0)
                    minimum_order_qty = col1.number_input("Minimum Order Quantity", min_value=1, step=1, value=int(selected.get("minimum_order_qty", 1) or 1))
                    available_for_public_sale = col1.checkbox("Available For Public Sale?", value=bool(selected.get("available_for_public_sale", False)))
                    available_for_mandi_network = col2.checkbox("Available For Mandi Network?", value=bool(selected.get("available_for_mandi_network", True)))
                    public_seller_manufacturer_id = col2.text_input("Public Seller Manufacturer ID", value=selected.get("public_seller_manufacturer_id", selected.get("created_by_manufacturer_id", "")))
                    visible = col1.checkbox("Visible to Active Catalog?", value=bool(selected.get("visible", True)))
                    image_url = st.text_input("Product Image URL", value=selected.get("image_url", ""))
                    admin_note = st.text_area("Admin Note", value=selected.get("admin_note", ""), height=100)
                    update_submit = st.form_submit_button("Save Product Updates")
                if update_submit:
                    product_catalog_service.update_product(
                        product_id=selected_id,
                        updated_by="PLATFORM_ADMIN",
                        updates={
                            "name": updated_name,
                            "category": updated_category,
                            "unit": updated_unit,
                            "description": updated_description,
                            "approved_mandi_price": approved_mandi_price,
                            "approved_mrp": approved_mrp,
                            "visibility_request": visibility_request,
                            "approved_visibility": approved_visibility,
                            "minimum_order_qty": minimum_order_qty,
                            "available_for_public_sale": available_for_public_sale,
                            "available_for_mandi_network": available_for_mandi_network,
                            "public_seller_manufacturer_id": public_seller_manufacturer_id,
                            "visible": visible,
                            "image_url": image_url,
                            "admin_note": admin_note,
                        },
                    )
                    st.success("Approved product updated.")
                    st.rerun()
                if st.button("Delete Selected Product", use_container_width=True):
                    product_catalog_service.delete_product(product_id=selected_id)
                    st.warning(f"{selected_id} deleted from catalog.")
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
            suggested_mrp = col2.number_input("Suggested MRP", min_value=0.0, step=1.0)
            visibility_request = col1.selectbox("Product Visibility Request", ["PUBLIC", "PRIVATE_CLIENT", "MANDI_NETWORK"], index=2)
            minimum_order_qty = col2.number_input("Minimum Order Quantity", min_value=1, step=1, value=1)
            available_for_public_sale = col1.checkbox("Available For Public Sale?")
            available_for_mandi_network = col2.checkbox("Available For Mandi Network?", value=True)
            image_url = st.text_input("Product Image URL", placeholder="Optional image URL")
            submitted = st.form_submit_button("Propose Product")
        if submitted and name and category and unit:
            created_by = user.manufacturer_code or ""
            app_context["product_catalog_service"].propose_product(
                created_by=created_by,
                created_by_email=user.email,
                name=name,
                category=category,
                unit=unit,
                description=description,
                suggested_mandi_price=suggested_mandi_price,
                suggested_mrp=suggested_mrp,
                visibility_request=visibility_request,
                minimum_order_qty=minimum_order_qty,
                available_for_public_sale=available_for_public_sale,
                available_for_mandi_network=available_for_mandi_network,
                image_url=image_url,
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
            st.info("No proposed products need your follow-up right now.")
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
                        "suggested_mrp": proposal.get("suggested_mrp", 0),
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
