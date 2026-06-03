from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.detail_drawer import render_catalog_detail_drawer
from components.empty_state import render_empty_state_block
from components.html_renderer import render_html
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_page_header, render_showcase_strip
from modules.profile.dashboard import render_public_buyer_profile_setup


def filter_marketplace_products(
    products: list[dict[str, Any]],
    *,
    search_term: str = "",
    category_filter: str = "All",
    max_price: float | None = None,
    in_stock_only: bool = False,
    sort_by: str = "Featured",
) -> list[dict[str, Any]]:
    normalized_search = search_term.strip().lower()
    filtered = [
        item
        for item in products
        if (category_filter == "All" or item.get("category") == category_filter)
        and (
            not normalized_search
            or normalized_search in str(item.get("name", "")).lower()
            or normalized_search in str(item.get("description", "")).lower()
        )
        and (max_price is None or float(item.get("approved_marketplace_price", item.get("marketplace_price", item.get("price", 0))) or 0) <= max_price)
        and (not in_stock_only or bool(item.get("visible", True)))
    ]
    if sort_by == "Price: Low to High":
        filtered.sort(key=lambda item: float(item.get("approved_marketplace_price", item.get("marketplace_price", item.get("price", 0))) or 0))
    elif sort_by == "Price: High to Low":
        filtered.sort(key=lambda item: float(item.get("approved_marketplace_price", item.get("marketplace_price", item.get("price", 0))) or 0), reverse=True)
    elif sort_by == "Newest":
        filtered.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    else:
        filtered.sort(key=lambda item: (int(item.get("minimum_order_qty", 1) or 1), str(item.get("name", "")).lower()))
    return filtered


def render_marketplace_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    role = user.role if user else "public_browse"
    is_public_buyer = bool(user and user.role == "public_buyer")
    products = app_context["product_catalog_service"].list_products(include_pending=False, viewer_role="public_buyer")
    image_service = app_context.get("image_service")
    favorites_service = app_context.get("favorites_service")
    trust_badge_service = app_context.get("trust_badge_service")
    cart_service = app_context.get("cart_service")
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

    max_marketplace_price = max(
        [float(item.get("approved_marketplace_price", item.get("marketplace_price", item.get("price", 0))) or 0) for item in products],
        default=0.0,
    )
    search_col, category_col = st.columns([2.2, 1.2])
    stock_col, sort_col = st.columns([1.1, 1.2])
    search_term = search_col.text_input("Search products", placeholder="Rice, atta, masala...")
    category_filter = category_col.selectbox("Category", ["All", *categories]) if categories else "All"
    in_stock_only = getattr(stock_col, "checkbox", lambda *_args, **_kwargs: False)("In stock", value=False)
    sort_by = getattr(sort_col, "selectbox", lambda _label, options, **_kwargs: options[0])(
        "Sort",
        ["Featured", "Newest", "Price: Low to High", "Price: High to Low"],
    )
    max_price = st.slider(
        "Price Range",
        min_value=0.0,
        max_value=float(max_marketplace_price or 1.0),
        value=float(max_marketplace_price or 1.0),
        step=1.0,
        disabled=not bool(max_marketplace_price),
    )
    filtered = filter_marketplace_products(
        products,
        search_term=search_term,
        category_filter=category_filter,
        max_price=max_price if max_marketplace_price else None,
        in_stock_only=in_stock_only,
        sort_by=sort_by,
    )
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
                <span class="mt-chip">Delivery: seller-confirmed dispatch</span>
              </div>
            </section>
            """
        )
    if not filtered:
        render_empty_state_block("No public products match the current search/filter.", icon="[]", cta="Adjust search or category")
    st.markdown("<div class='mt-public-product-grid mt-card-grid'>", unsafe_allow_html=True)
    for index, item in enumerate(filtered[:8]):
        image = image_service.get_display_image(item, label=str(item.get("name", "Product"))) if image_service else {"src": "", "alt": str(item.get("name", "Product")), "status": "NONE"}
        trust_badges = trust_badge_service.badges_for_marketplace_product(item) if trust_badge_service else []
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
            badges=trust_badges,
            supporting_text=str(item.get("description", "") or "Public marketplace product."),
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
    public_cart_service = app_context["public_cart_service"]
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
            trust_badges = trust_badge_service.badges_for_marketplace_product(selected) if trust_badge_service else []
            render_catalog_detail_drawer(
                title=str(selected.get("name", "Product")),
                subtitle=str(selected.get("category", "General")),
                image=image,
                price_label="Marketplace",
                price_value=str(selected.get("approved_marketplace_price", selected.get("marketplace_price", selected.get("price", 0)))),
                availability_label=f"MOQ {selected.get('minimum_order_qty', 1)}",
                metadata={
                    "Unit": str(selected.get("unit", "unit")),
                    "Dispatch": "Seller confirmed",
                    "Availability": "In stock" if selected.get("visible", True) else "Check seller",
                },
                badges=trust_badges,
                description=str(selected.get("description", "") or "Public marketplace catalog product."),
            )
            qty = st.number_input(
                "Quantity",
                min_value=max(int(selected.get("minimum_order_qty", 1) or 1), 1),
                step=max(int(selected.get("minimum_order_qty", 1) or 1), 1),
                value=max(int(selected.get("minimum_order_qty", 1) or 1), 1),
            )
            if st.button("Add To Cart", use_container_width=True):
                try:
                    public_cart_service.add_item(buyer["public_buyer_id"], product_id=selected_product_id, qty=int(qty))
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
        cart = public_cart_service.get_cart(buyer["public_buyer_id"])
        if not cart.get("items"):
            render_empty_state_block("Your public cart is empty.", icon="[]", cta="Add products from Browse + Add To Cart")
        else:
            for item in cart.get("items", []):
                row_left, row_mid, row_right = st.columns([2.4, 1.2, 0.8])
                row_left.markdown(
                    f"**{str(item.get('product_name', item.get('product_id', 'Product')))}**\n\n"
                    f"Price: {str(item.get('marketplace_price', item.get('price', 0)))} | "
                    f"Qty: {str(item.get('qty', 1))}"
                )
                new_qty = row_mid.number_input(
                    f"Qty {item.get('item_id', '')}",
                    min_value=1,
                    value=max(int(item.get("qty", 1) or 1), 1),
                    step=1,
                    key=f"marketplace_cart_qty_{item.get('item_id', '')}",
                )
                if cart_service and new_qty != int(item.get("qty", 1) or 1):
                    cart_service.update_qty(
                        "public_buyer",
                        buyer["public_buyer_id"],
                        cart_type="MARKETPLACE",
                        item_id=str(item.get("item_id", "")),
                        qty=int(new_qty),
                    )
                    st.rerun()
                if row_right.button("Remove", key=f"marketplace_remove_{item.get('item_id', '')}", use_container_width=True):
                    if cart_service:
                        cart_service.remove_item(
                            "public_buyer",
                            buyer["public_buyer_id"],
                            cart_type="MARKETPLACE",
                            item_id=str(item.get("item_id", "")),
                        )
                    else:
                        public_cart_service.clear_cart(buyer["public_buyer_id"])
                    st.rerun()
            st.caption(f"Subtotal: {cart.get('subtotal', 0)}")
            st.caption("Estimated delivery: seller dispatch after payment verification.")
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
