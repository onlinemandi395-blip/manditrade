from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_mobile_record_card, render_page_header


def render_product_approvals_dashboard(app_context: dict) -> None:
    product_catalog_service = app_context["product_catalog_service"]
    current_user = app_context["current_user"]
    products = app_context["governance_service"].list_products()
    proposed_products = [item for item in products if item.get("status") == "PROPOSED"]

    render_page_header(
        "Product Approvals",
        "Review manufacturer product proposals and activate only the approved catalog records.",
        ["Platform Admin", "Approval Queue"],
        role="Platform Admin",
        metrics=[("Queue Type", "Proposal review"), ("Clarifications", "In-thread")],
        kicker="Digital Manpur Approval Deck",
    )
    render_metric_grid(
        [
            render_metric_card("Proposed Products", str(len(proposed_products)), "PENDING"),
            render_metric_card("Active Products", str(len([item for item in products if item.get('status') == 'ACTIVE'])), "SUCCESS"),
            render_metric_card("Rejected Products", str(len([item for item in products if item.get('status') == 'REJECTED'])), "WARNING"),
        ]
    )
    render_section_intro("Approval Queue", "Platform admin captures final mandi, B2B, and marketplace pricing before activation.")
    if proposed_products:
        preview = "".join(
            render_mobile_record_card(
                {
                    "Product": item.get("name", item.get("product_id", "")),
                    "Suggested Mandi": item.get("suggested_mandi_price", 0),
                    "Visibility": item.get("visibility_request", "MANDI_NETWORK"),
                    "Clarification": item.get("clarification_status", "NONE"),
                }
            )
            for item in proposed_products[:3]
        )
        render_html(f"<section class='mt-card-stack'>{preview}</section>")
    st.dataframe(proposed_products, use_container_width=True)
    if not proposed_products:
        st.success("No proposed products are waiting for review.")
        return

    selected_id = st.selectbox("Select Proposed Product", [item["product_id"] for item in proposed_products])
    selected = next(item for item in proposed_products if item["product_id"] == selected_id)
    st.markdown("### Proposal Snapshot")
    st.json(
        {
            "name": selected.get("name", ""),
            "description": selected.get("description", ""),
            "suggested_mandi_price": selected.get("suggested_mandi_price", 0),
            "suggested_b2b_price": selected.get("suggested_client_price", selected.get("suggested_mrp", 0)),
            "suggested_marketplace_price": selected.get("suggested_marketplace_price", selected.get("suggested_mrp", 0)),
            "visibility_request": selected.get("visibility_request", "MANDI_NETWORK"),
            "minimum_order_qty": selected.get("minimum_order_qty", 1),
            "available_for_public_sale": selected.get("available_for_public_sale", False),
            "available_for_mandi_network": selected.get("available_for_mandi_network", True),
            "clarification_status": selected.get("clarification_status", "NONE"),
        },
        expanded=False,
    )
    st.markdown("### Comment Thread")
    comments = product_catalog_service.list_product_comments(selected_id, current_user)
    if comments:
        st.dataframe(comments, use_container_width=True)
    else:
        st.info("No proposal comments yet.")

    with st.form(f"admin_product_comment_{selected_id}"):
        admin_comment = st.text_area("Comment / Query", height=100)
        send_comment = st.form_submit_button("Send Comment")
    if send_comment and admin_comment.strip():
        product_catalog_service.add_product_comment(selected_id, current_user, admin_comment)
        st.success("Admin comment added.")
        st.rerun()

    if st.button("Mark Clarification Resolved", use_container_width=True):
        product_catalog_service.mark_clarification_resolved(selected_id, current_user)
        st.success("Clarification marked as resolved.")
        st.rerun()

    col1, col2 = st.columns(2)
    mandi_price = col1.number_input("Approved Mandi Price", min_value=0.0, step=1.0, value=float(selected.get("suggested_mandi_price", selected.get("mandi_price", 0)) or 0))
    client_price = col2.number_input("Approved B2B Price", min_value=0.0, step=1.0, value=float(selected.get("suggested_client_price", selected.get("client_price", selected.get("mrp", 0))) or 0))
    marketplace_price = col1.number_input("Approved Marketplace Price", min_value=0.0, step=1.0, value=float(selected.get("suggested_marketplace_price", selected.get("marketplace_price", selected.get("mrp", 0))) or 0))
    category = col1.text_input("Category", value=selected.get("category", ""))
    unit = col2.text_input("Unit", value=selected.get("unit", "kg"))
    approved_visibility = st.selectbox(
        "Approved Visibility",
        ["PUBLIC", "B2B", "MANDI_NETWORK"],
        index=["PUBLIC", "B2B", "MANDI_NETWORK"].index(
            "B2B" if selected.get("visibility_request", "MANDI_NETWORK") == "PRIVATE_CLIENT" else selected.get("visibility_request", "MANDI_NETWORK")
        )
        if ("B2B" if selected.get("visibility_request", "MANDI_NETWORK") == "PRIVATE_CLIENT" else selected.get("visibility_request", "MANDI_NETWORK")) in {"PUBLIC", "B2B", "MANDI_NETWORK"}
        else 2,
    )
    public_seller_manufacturer_id = st.text_input(
        "Public Seller Manufacturer ID",
        value=selected.get("public_seller_manufacturer_id", selected.get("created_by_manufacturer_id", "")),
        help="Used only for PUBLIC marketplace fulfilment.",
    )
    admin_note = st.text_area("Admin Note", value=selected.get("admin_note", ""), height=100)
    clarification_status = selected.get("clarification_status", "NONE")
    if clarification_status == "ADMIN_QUERY":
        st.warning("Approval is blocked until the manufacturer replies or the clarification is marked resolved.")

    approve_col, reject_col = st.columns(2)
    if approve_col.button("Approve Product", use_container_width=True):
        try:
            product_catalog_service.approve_product(
                product_id=selected_id,
                approved_by="PLATFORM_ADMIN",
                approved_mandi_price=mandi_price,
                approved_client_price=client_price,
                approved_marketplace_price=marketplace_price,
                category=category,
                unit=unit,
                approved_visibility="PRIVATE_CLIENT" if approved_visibility == "B2B" else approved_visibility,
                visible=True,
                admin_note=admin_note,
            )
            if public_seller_manufacturer_id.strip():
                product_catalog_service.update_product(
                    product_id=selected_id,
                    updated_by="PLATFORM_ADMIN",
                    updates={"public_seller_manufacturer_id": public_seller_manufacturer_id.strip()},
                )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success("Product approved and activated.")
            st.rerun()
    if reject_col.button("Reject Product", use_container_width=True):
        product_catalog_service.reject_product(
            product_id=selected_id,
            approved_by="PLATFORM_ADMIN",
            admin_note=admin_note,
        )
        st.warning("Product marked as rejected.")
        st.rerun()
