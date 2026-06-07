from __future__ import annotations

import streamlit as st

from services.pricing_service import PricingService


def render_product_card(product: dict, *, view: str = "marketplace", on_add_to_cart=None, media_service=None) -> None:
    pricing_service = PricingService()
    images = [dict(image or {}) for image in (product.get("images", []) or [])]
    primary_image = next((image for image in images if image.get("is_primary")), images[0] if images else {})
    marketplace = (product.get("sales_channels") or {}).get("marketplace", {})
    manditrade = (product.get("sales_channels") or {}).get("manditrade", {})
    pricing = dict(product.get("pricing", {}) or {})
    owner = dict(product.get("owner", {}) or {})
    inventory = dict(product.get("inventory", {}) or {})
    with st.container(border=True):
        media = st.empty()
        renderable = media_service.get_renderable_image(primary_image) if media_service else {"render_mode": "placeholder", "bytes": None, "url": "", "error": ""}
        if renderable["render_mode"] == "bytes" and renderable.get("bytes"):
            media.image(renderable["bytes"], use_container_width=True)
        elif renderable["render_mode"] == "url" and renderable.get("url"):
            media.image(renderable["url"], use_container_width=True)
        else:
            media.markdown("<div class='mt-product-card__media'>No Image</div>", unsafe_allow_html=True)
        st.markdown(f"#### {product.get('product_name', product.get('product_id', 'Product'))}")
        st.caption(f"{product.get('product_code', '')} | {product.get('category', 'General')} | {product.get('status', 'ACTIVE')}")
        if view == "marketplace":
            valid_price, price_error = pricing_service.validate_channel_price(product, "marketplace")
            if valid_price:
                st.write(f"Marketplace Price: {pricing_service.resolve_sell_price(product, 'marketplace')}")
            else:
                st.error(price_error)
            if valid_price and st.button("Add to Cart", key=f"cart_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        elif view == "manditrade":
            valid_price, price_error = pricing_service.validate_channel_price(product, "manditrade")
            if valid_price:
                st.write(f"MandiTrade Price: {pricing_service.resolve_sell_price(product, 'manditrade')}")
            else:
                st.error(price_error)
            st.caption(f"Inventory: {inventory.get('available_quantity', 0)} {product.get('unit', 'piece')}")
            if valid_price and st.button("Request / Order", key=f"request_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        else:
            marketplace_price = pricing.get("marketplace_price", "")
            manditrade_price = pricing.get("manditrade_price", "")
            st.write(f"Marketplace: {'On' if marketplace.get('enabled') else 'Off'} | Price: {marketplace_price}")
            st.write(f"MandiTrade: {'On' if manditrade.get('enabled') else 'Off'} | Price: {manditrade_price}")
            st.caption(f"Admin Price: {pricing.get('admin_price', 0)}")
            st.caption(f"Owner: {owner.get('email', '-')}")
            st.caption(f"Owner Role: {owner.get('role', '-')}")
            st.caption(f"Inventory: {inventory.get('available_quantity', 0)} {product.get('unit', 'piece')}")
        gallery_images = []
        if media_service:
            for image in images:
                renderable_image = media_service.get_renderable_image(image)
                if renderable_image["render_mode"] == "bytes" and renderable_image.get("bytes"):
                    gallery_images.append(renderable_image["bytes"])
                elif renderable_image["render_mode"] == "url" and renderable_image.get("url"):
                    gallery_images.append(renderable_image["url"])
        else:
            gallery_images = [
                image.get("direct_render_url") or image.get("thumbnail_link") or image.get("web_content_link")
                for image in images
                if image.get("direct_render_url") or image.get("thumbnail_link") or image.get("web_content_link")
            ]
        if len(gallery_images) > 1:
            with st.expander(f"Gallery ({len(gallery_images)})", expanded=False):
                st.image(gallery_images, width=120)
