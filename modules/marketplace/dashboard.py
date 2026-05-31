from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header, render_showcase_strip


def render_marketplace_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    role = user.role if user else "public_browse"
    products = app_context["product_catalog_service"].list_products(include_pending=False, viewer_role="public_buyer")
    render_page_header(
        "Marketplace",
        "Instant-pay public shopping stays separate from the private proposal-and-khata workflow used by manufacturer clients.",
        ["Public Catalog", "Instant Pay", "Public Visibility Only"],
        role=role.replace("_", " ").title(),
        metrics=[("Visible Products", str(len(products))), ("Checkout Model", "100% upfront")],
        kicker="Digital Manpur Public Marketplace",
    )
    categories = sorted({item.get("category", "Uncategorized") for item in products})
    render_metric_grid(
        [
            render_metric_card("Public Products", str(len(products)), "SUCCESS"),
            render_metric_card("Categories", str(len(categories)), "OPEN"),
            render_metric_card("Flow", "Instant Pay", "PENDING"),
        ]
    )
    render_showcase_strip(
        [
            ("Public Buyers", "MRP only", "SUCCESS"),
            ("Private Clients", "Proposal flow retained", "OPEN"),
            ("Manufacturers", "Preview + fulfilment", "PENDING"),
        ]
    )

    search_col, category_col = st.columns([2, 1])
    search_term = search_col.text_input("Search products", placeholder="Rice, atta, masala...")
    category_filter = category_col.selectbox("Category", ["All", *categories]) if categories else "All"
    filtered = [
        item
        for item in products
        if (category_filter == "All" or item.get("category") == category_filter)
        and (
            not search_term.strip()
            or search_term.strip().lower() in str(item.get("name", "")).lower()
            or search_term.strip().lower() in str(item.get("description", "")).lower()
        )
    ]
    render_section_intro("Public Catalog", "Only ACTIVE, PUBLIC, public-sale-enabled products are visible here. No mandi price, RFQ, inventory, or internal seller notes are exposed.")
    preview_cards = "".join(
        f"""
        <article class="mt-product-card">
          <div class="mt-product-card__image"></div>
          <h3>{escape(str(item.get('name', 'Product')))}</h3>
          <p>{escape(str(item.get('description', '') or 'Public marketplace catalog product.'))}</p>
          <div class="mt-chip-row">
            <span class="mt-price-chip">Price: {escape(str(item.get('approved_marketplace_price', item.get('marketplace_price', item.get('price', 0)))))}</span>
            <span class="mt-chip">{escape(str(item.get('category', 'General')))}</span>
            <span class="mt-chip">MOQ: {escape(str(item.get('minimum_order_qty', 1)))}</span>
          </div>
        </article>
        """
        for item in filtered[:6]
    )
    if preview_cards:
        render_html(f"<section class='mt-grid mt-grid--actions'>{preview_cards}</section>")
    st.dataframe(filtered, use_container_width=True)

    if not user:
        st.info("Use the global MandiTrade Google login to continue.")
        return

    if user.role != "public_buyer":
        st.info("Marketplace preview is visible for this role. Public cart and checkout are enabled only for signed-in public buyers.")
        return

    buyer = app_context["public_buyer_service"].get_by_email(user.email)
    if not buyer:
        st.error("Public buyer profile not found for this account.")
        return
    cart_service = app_context["public_cart_service"]
    order_service = app_context["public_order_service"]
    activity_tab, cart_tab = st.tabs(["Browse + Add To Cart", "Cart + Checkout"])
    with activity_tab:
        if not filtered:
            st.info("No public products match the current search/filter.")
        else:
            selected_product_id = st.selectbox("Select Product", [item["product_id"] for item in filtered], format_func=lambda pid: next(item["name"] for item in filtered if item["product_id"] == pid))
            selected = next(item for item in filtered if item["product_id"] == selected_product_id)
            qty = st.number_input(
                "Quantity",
                min_value=max(int(selected.get("minimum_order_qty", 1) or 1), 1),
                step=max(int(selected.get("minimum_order_qty", 1) or 1), 1),
                value=max(int(selected.get("minimum_order_qty", 1) or 1), 1),
            )
            if st.button("Add To Cart", use_container_width=True):
                try:
                    cart_service.add_item(buyer["public_buyer_id"], product_id=selected_product_id, qty=int(qty))
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success("Product added to public cart.")
                    st.rerun()
    with cart_tab:
        cart = cart_service.get_cart(buyer["public_buyer_id"])
        st.json(cart, expanded=False)
        if not cart.get("items"):
            st.info("Your public cart is empty.")
        else:
            st.info("Public checkout uses approved MRP only and requires 100% upfront payment.")
            if st.button("Create Public Order", use_container_width=True):
                try:
                    order = order_service.create_order_from_cart(buyer["public_buyer_id"])
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"Public order created: {order['public_order_id']}")
                    st.code(order_service.build_payment_instruction_text(order))
                    st.rerun()
