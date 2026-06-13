from __future__ import annotations

import streamlit as st

from components.image_slideshow import open_slideshow
from services.pricing_service import PricingService


def render_product_card(
    product: dict,
    *,
    view: str = "marketplace",
    on_add_to_cart=None,
    media_service=None,
    return_route: str = "",
    card_context: str = "",
    translator=None,
    ui_config: dict | None = None,
) -> None:
    pricing_service = PricingService()
    t = translator.t if translator else (lambda key: key)
    gallery_card_config = dict((((ui_config or {}).get("product_gallery") or {}).get("card") or {}))
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
        image_count = len(images)
        badge_mode = str(gallery_card_config.get("badge_mode", "counter") or "counter").strip().lower()
        if badge_mode == "count":
            badge_label = f"{image_count} {t('ui.images')}" if image_count else t("ui.no_images")
        else:
            badge_label = f"{1 if image_count else 0} / {image_count}" if image_count > 1 else (t("ui.one_image") if image_count == 1 else t("ui.no_images"))
        button_label = str(gallery_card_config.get("open_button_label_key", "ui.open_images") or "ui.open_images")
        if st.button(
            f"{t(button_label)} ({badge_label})",
            key=f"open_slideshow_{view}_{return_route}_{card_context}_{product.get('product_id', '')}",
            use_container_width=True,
            disabled=not bool(images),
        ):
            open_slideshow(product_id=product.get("product_id", ""), return_route=return_route)
            st.rerun()
        st.markdown(f"#### {product.get('product_name', product.get('product_id', t('ui.product')))}")
        st.caption(f"{product.get('product_code', '')} | {product.get('category', 'General')} | {product.get('status', 'ACTIVE')}")
        if view == "marketplace":
            valid_price, price_error = pricing_service.validate_channel_price(product, "marketplace")
            if valid_price:
                st.write(f"{t('field.marketplace_price')}: {pricing_service.resolve_sell_price(product, 'marketplace')}")
            else:
                st.error(price_error)
            if valid_price and st.button(t("action.add_to_cart"), key=f"cart_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        elif view == "manditrade":
            valid_price, price_error = pricing_service.validate_channel_price(product, "manditrade")
            if valid_price:
                st.write(f"{t('field.manditrade_price')}: {pricing_service.resolve_sell_price(product, 'manditrade')}")
            else:
                st.error(price_error)
            st.caption(f"{t('ui.inventory')}: {inventory.get('available_quantity', 0)} {product.get('unit', 'piece')}")
            if valid_price and st.button(t("ui.request_order"), key=f"request_{product.get('product_id', '')}", use_container_width=True) and on_add_to_cart:
                on_add_to_cart(product)
        else:
            marketplace_price = pricing.get("marketplace_price", "")
            manditrade_price = pricing.get("manditrade_price", "")
            st.write(f"{t('module.marketplace.title')}: {t('ui.on') if marketplace.get('enabled') else t('ui.off')} | {t('field.price')}: {marketplace_price}")
            st.write(f"{t('module.manditrade.title')}: {t('ui.on') if manditrade.get('enabled') else t('ui.off')} | {t('field.price')}: {manditrade_price}")
            st.caption(f"{t('field.admin_price')}: {pricing.get('admin_price', 0)}")
            st.caption(f"{t('ui.owner')}: {owner.get('email', '-')}")
            st.caption(f"{t('ui.owner_role')}: {owner.get('role', '-')}")
            st.caption(f"{t('ui.inventory')}: {inventory.get('available_quantity', 0)} {product.get('unit', 'piece')}")
