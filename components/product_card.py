from __future__ import annotations

import streamlit as st


def render_product_card(product: dict, *, view: str = "marketplace", on_add_to_cart=None) -> None:
    images = [dict(image or {}) for image in (product.get("images", []) or [])]
    primary_image = next((image for image in images if image.get("is_primary")), images[0] if images else {})
    image_url = str(
        primary_image.get("direct_render_url", "")
        or primary_image.get("thumbnail_link", "")
        or primary_image.get("web_content_link", "")
        or product.get("image_url", "")
        or ""
    ).strip()
    marketplace = (product.get("sales_channels") or {}).get("marketplace", {})
    manditrade = (product.get("sales_channels") or {}).get("manditrade", {})
    owner = dict(product.get("owner", {}) or {})
    inventory = dict(product.get("inventory", {}) or {})
    with st.container(border=True):
        media = st.empty()
        if image_url:
            media.image(image_url, use_container_width=True)
        else:
            media.markdown("<div class='mt-product-card__media'>No Image</div>", unsafe_allow_html=True)
        st.markdown(f"#### {product.get('product_name', product.get('product_id', 'Product'))}")
        st.caption(f"{product.get('product_code', '')} | {product.get('category', 'General')} | {product.get('status', 'ACTIVE')}")
        if view == "marketplace":
            st.write(f"Marketplace Price: {marketplace.get('price', 0)}")
            if st.button("Add to Cart", key=f"cart_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        elif view == "manditrade":
            st.write(f"MandiTrade Price: {manditrade.get('price', 0)}")
            st.caption(f"Inventory: {inventory.get('available_quantity', 0)} {product.get('unit', 'piece')}")
            if st.button("Request / Order", key=f"request_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        else:
            st.write(f"Marketplace: {'On' if marketplace.get('enabled') else 'Off'} | Price: {marketplace.get('price', 0)}")
            st.write(f"MandiTrade: {'On' if manditrade.get('enabled') else 'Off'} | Price: {manditrade.get('price', 0)}")
            st.caption(f"Owner: {owner.get('email', '-')}")
            st.caption(f"Owner Role: {owner.get('role', '-')}")
            st.caption(f"Inventory: {inventory.get('available_quantity', 0)} {product.get('unit', 'piece')}")
        gallery_urls = [
            image.get("direct_render_url") or image.get("thumbnail_link") or image.get("web_content_link")
            for image in images
            if image.get("direct_render_url") or image.get("thumbnail_link") or image.get("web_content_link")
        ]
        if len(gallery_urls) > 1:
            with st.expander(f"Gallery ({len(gallery_urls)})", expanded=False):
                st.image(gallery_urls, width=120)
