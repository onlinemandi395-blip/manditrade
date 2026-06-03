from __future__ import annotations

from html import escape

import streamlit as st

from components.empty_state import render_empty_state_block
from components.html_renderer import render_html
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_page_header, render_showcase_strip
from modules.profile.dashboard import render_public_buyer_profile_setup


def render_marketplace_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    role = user.role if user else "public_browse"
    is_public_buyer = bool(user and user.role == "public_buyer")
    products = app_context["product_catalog_service"].list_products(include_pending=False, viewer_role="public_buyer")
    image_service = app_context.get("image_service")
    favorites_service = app_context.get("favorites_service")
    render_platform_shell(
        title="Marketplace",
        subtitle="Instant-pay public shopping stays separate from the manufacturer-facing MandiPlace and raw-material supply workflows.",
        badges=["Public Catalog", "Instant Pay", "Public Visibility Only"],
        role=role.replace("_", " ").title(),
        metrics=[("Visible Products", str(len(products))), ("Checkout Model", "100% upfront")],
        kicker="Digital Manpur Public Marketplace",
        breadcrumbs=["Workspace", "Commerce", "Marketplace"],
        primary_actions=["Browse Public Catalog"],
    )
    categories = sorted({item.get("category", "Uncategorized") for item in products})
    if not is_public_buyer:
        render_kpi_cards(
            [
                {"label": "Public Products", "value": str(len(products)), "status": "SUCCESS"},
                {"label": "Categories", "value": str(len(categories)), "status": "OPEN"},
                {"label": "Flow", "value": "Instant Pay", "status": "PENDING"},
            ]
        )
        render_showcase_strip(
            [
                ("Public Buyers", "MRP only", "SUCCESS"),
                ("MandiPlace Buyers", "B2B lane separate", "OPEN"),
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
    render_section_intro(
        "Public Catalog",
        "Browse products, compare public pricing, and add items to cart from one clean marketplace grid."
        if is_public_buyer
        else "Browse public products, compare pricing, and place upfront-pay orders from one simple marketplace view.",
    )
    if is_public_buyer:
        cart_count = 0
        buyer_preview = app_context["public_buyer_service"].get_by_email(user.email)
        if buyer_preview:
            cart_count = len(app_context["public_cart_service"].get_cart(buyer_preview["public_buyer_id"]).get("items", []))
        render_html(
            f"""
            <section class="mt-public-marketplace-toolbar">
              <div class="mt-chip-row">
                <span class="mt-chip">Products: {escape(str(len(filtered)))}</span>
                <span class="mt-chip">Categories: {escape(str(len(categories)))}</span>
                <span class="mt-price-chip">Cart: {escape(str(cart_count))}</span>
              </div>
            </section>
            """
        )
    if not filtered:
        render_empty_state_block("No public products match the current search/filter.", icon="[]", cta="Adjust search or category")
    st.markdown("<div class='mt-public-product-grid mt-card-grid'>", unsafe_allow_html=True)
    for index, item in enumerate(filtered[:8]):
        image = image_service.get_display_image(item, label=str(item.get("name", "Product"))) if image_service else {"src": "", "alt": str(item.get("name", "Product")), "status": "NONE"}
        clicked = render_product_card(
            item=item,
            variant="MARKETPLACE_PRODUCT",
            image=image,
            title=str(item.get("name", "Product")),
            subtitle=str(item.get("category", "General")),
            price_label="Marketplace",
            price_value=str(item.get("approved_marketplace_price", item.get("marketplace_price", item.get("price", 0)))),
            availability_label=f"MOQ {item.get('minimum_order_qty', 1)}",
            visibility_label="PUBLIC",
            action_label="View Details",
            action_key=f"marketplace_view_{item.get('product_id', index)}",
        )
        if clicked:
            st.session_state["marketplace_selected_product"] = item.get("product_id", "")
    st.markdown("</div>", unsafe_allow_html=True)

    if not user:
        st.info("Sign in from the sidebar to continue.")
        return

    if user.role != "public_buyer":
        st.info("Marketplace preview is visible for this role. Public cart and checkout are enabled only for signed-in public buyers.")
        return

    buyer = app_context["public_buyer_service"].get_by_email(user.email)
    if not buyer:
        st.error("Public buyer profile not found for this account.")
        return
    if not app_context["public_buyer_service"].is_profile_complete(buyer):
        render_public_buyer_profile_setup(app_context, welcome_mode=True)
        return
    cart_service = app_context["public_cart_service"]
    order_service = app_context["public_order_service"]
    activity_tab, cart_tab = st.tabs(["Browse + Add To Cart", "Cart + Checkout"])
    with activity_tab:
        if not filtered:
            render_empty_state_block("No public products match the current search/filter.", icon="[]", cta="Adjust filters")
        else:
            selected_product_id = str(st.session_state.get("marketplace_selected_product") or filtered[0]["product_id"])
            if not any(item["product_id"] == selected_product_id for item in filtered):
                selected_product_id = filtered[0]["product_id"]
            selected_product_id = st.selectbox("Selected Product", [item["product_id"] for item in filtered], format_func=lambda pid: next(item["name"] for item in filtered if item["product_id"] == pid), index=[item["product_id"] for item in filtered].index(selected_product_id))
            selected = next(item for item in filtered if item["product_id"] == selected_product_id)
            image = image_service.get_display_image(selected, label=str(selected.get("name", "Product"))) if image_service else {"src": "", "alt": str(selected.get("name", "Product")), "status": "NONE"}
            render_html(
                f"""
                <article class="mt-product-card">
                  <div class="mt-product-thumbnail" style="background-image:url('{escape(image['src'])}');" role="img" aria-label="{escape(image['alt'])}"></div>
                  <h3>{escape(str(selected.get('name', 'Product')))}</h3>
                  <p>{escape(str(selected.get('description', '') or 'Public marketplace catalog product.'))}</p>
                  <div class="mt-chip-row">
                    <span class="mt-price-chip">Marketplace: {escape(str(selected.get('approved_marketplace_price', selected.get('marketplace_price', selected.get('price', 0)))))}</span>
                    <span class="mt-chip">{escape(str(selected.get('category', 'General')))}</span>
                    <span class="mt-availability-chip">MOQ {escape(str(selected.get('minimum_order_qty', 1)))}</span>
                  </div>
                </article>
                """
            )
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
            if favorites_service and st.button("Save To Favorites", use_container_width=True):
                favorites_service.save_favorite(
                    "public_buyer",
                    buyer["public_buyer_id"],
                    item_type="PRODUCT",
                    item_id=selected_product_id,
                    title=str(selected.get("name", "Product")),
                    subtitle=str(selected.get("category", "General")),
                    image_url=str(image.get("src", "")),
                )
                st.success("Saved to favorites.")
                st.rerun()
    with cart_tab:
        cart = cart_service.get_cart(buyer["public_buyer_id"])
        if not cart.get("items"):
            render_empty_state_block("Your public cart is empty.", icon="[]", cta="Add products from Browse + Add To Cart")
        else:
            st.dataframe(cart.get("items", []), use_container_width=True)
            st.caption(f"Subtotal: {cart.get('subtotal', 0)}")
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
        if favorites_service:
            favorites = favorites_service.list_favorites("public_buyer", buyer["public_buyer_id"])
            st.caption(f"Saved Products: {len(favorites)}")
