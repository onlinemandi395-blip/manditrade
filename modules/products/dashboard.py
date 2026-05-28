from __future__ import annotations

import streamlit as st

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
    render_page_header("Products", "Govern public mandi catalog, approvals, and pricing without slipping back into ERP complexity.", ["Public Catalog", "Mandi Price", "MRP"])
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
    render_section_intro("Catalog Governance", "Manufacturers can propose products and platform admin approves them with mandi price and MRP.")
    st.dataframe(products, use_container_width=True)
    if not user or user.role not in {"manufacturer", "admin_as_manufacturer"}:
        if user and user.role == "platform_admin":
            st.info("Use the dedicated Product Approvals page to review and activate proposed products.")
        return

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
    if not own_proposals:
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
