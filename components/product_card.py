from __future__ import annotations

import base64
import html

import streamlit as st

from components.html_renderer import render_template
from components.image_slideshow import open_slideshow
from services.payment_service import PaymentService
from services.pricing_service import PricingService


def _build_thumbnail_markup(primary_image: dict, media_service) -> str:
    renderable = media_service.get_renderable_image(primary_image) if media_service and primary_image else {
        "render_mode": "placeholder",
        "bytes": None,
        "url": "",
    }
    if renderable.get("render_mode") == "bytes" and renderable.get("bytes"):
        encoded = base64.b64encode(renderable["bytes"]).decode("ascii")
        return f"<div class='mt-catalog-card__thumb'><img src='data:image/png;base64,{encoded}' alt='Product image'></div>"
    if renderable.get("render_mode") == "url" and renderable.get("url"):
        return (
            "<div class='mt-catalog-card__thumb'>"
            f"<img src='{html.escape(str(renderable['url']))}' alt='Product image'>"
            "</div>"
        )
    return "<div class='mt-catalog-card__thumb-placeholder'>No Image</div>"


def render_product_card(
    product: dict,
    *,
    view: str = "marketplace",
    on_add_to_cart=None,
    on_buy_now=None,
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
    owner_business_details = dict(product.get("owner_business_details", {}) or {})
    inventory = dict(product.get("inventory", {}) or {})
    manditrade_rules = dict(((product.get("sales_channels") or {}).get("manditrade") or {}))
    merchant_upi_id = str(owner_business_details.get("upi_id", "")).strip()
    merchant_payee_name = str(
        owner_business_details.get("business_name", "") or owner.get("display_name", "") or owner.get("email", "")
    ).strip()
    merchant_upi_link = ""
    if merchant_upi_id:
        merchant_upi_link = PaymentService.build_upi_link_from_values(
            upi_id=merchant_upi_id,
            payee_name=merchant_payee_name or "Merchant",
            amount=float(pricing_service.resolve_sell_price(product, view) or 0) if view in {"marketplace", "manditrade"} else 0,
            currency=str(pricing.get("currency", "INR")).strip() or "INR",
            reference=str(product.get("product_id", "")).strip() or "PRODUCT",
        )

    title = html.escape(str(product.get("product_name", product.get("product_id", t("ui.product")))))
    meta = html.escape(f"{product.get('category', 'General')} | {product.get('subcategory', 'General')}")
    thumbnail_markup = _build_thumbnail_markup(primary_image, media_service)
    image_count = len(images)
    badge_mode = str(gallery_card_config.get("badge_mode", "counter") or "counter").strip().lower()
    if badge_mode == "count":
        image_badge = f"{image_count} {t('ui.images')}" if image_count else t("ui.no_images")
    else:
        image_badge = f"{1 if image_count else 0} / {image_count}" if image_count > 1 else (t("ui.one_image") if image_count == 1 else t("ui.no_images"))

    price_label = "-"
    badge_label = image_badge
    promise_label = "Preview ready"
    details = []

    if view == "marketplace":
        valid_price, price_error = pricing_service.validate_channel_price(product, "marketplace")
        if valid_price:
            price_label = f"Rs. {float(pricing_service.resolve_sell_price(product, 'marketplace') or 0):g}"
            badge_label = "B2C"
            promise_label = "Ready for direct purchase"
            details = [
                f"<span class='mt-catalog-card__detail'>{html.escape(t('ui.inventory'))}: {inventory.get('available_quantity', 0)} {html.escape(str(product.get('unit', 'piece')))}</span>",
                f"<span class='mt-catalog-card__detail'>{image_badge}</span>",
            ]
            if merchant_upi_id and view == "marketplace":
                details.append(f"<span class='mt-catalog-card__detail'>Merchant UPI: {html.escape(merchant_upi_id)}</span>")
        else:
            st.error(price_error)
    elif view == "manditrade":
        valid_price, price_error = pricing_service.validate_channel_price(product, "manditrade")
        if valid_price:
            price_label = f"Rs. {float(pricing_service.resolve_sell_price(product, 'manditrade') or 0):g}"
            badge_label = "B2B"
            promise_label = "Bulk order ready"
            details = [
                f"<span class='mt-catalog-card__detail'>{html.escape(t('ui.minimum_quantity'))}: {float(manditrade_rules.get('minimum_quantity', 1) or 1):g}</span>",
                f"<span class='mt-catalog-card__detail'>{html.escape(t('ui.increment_quantity'))}: {float(manditrade_rules.get('increment_quantity', 1) or 1):g}</span>",
                f"<span class='mt-catalog-card__detail'>{html.escape(t('ui.inventory'))}: {inventory.get('available_quantity', 0)} {html.escape(str(product.get('unit', 'piece')))}</span>",
            ]
        else:
            st.error(price_error)
    else:
        price_label = f"Rs. {float(pricing.get('admin_price', 0) or 0):g}"
        badge_label = "Admin"
        promise_label = "Catalog control"
        details = [
            f"<span class='mt-catalog-card__detail'>{html.escape(t('module.marketplace.title'))}: {html.escape(t('ui.on') if marketplace.get('enabled') else t('ui.off'))}</span>",
            f"<span class='mt-catalog-card__detail'>{html.escape(t('module.manditrade.title'))}: {html.escape(t('ui.on') if manditrade.get('enabled') else t('ui.off'))}</span>",
            f"<span class='mt-catalog-card__detail'>{html.escape(t('ui.owner'))}: {html.escape(str(owner.get('email', '-')))}</span>",
        ]

    render_template(
        "catalog_product_card.html",
        view=view,
        thumbnail_markup=thumbnail_markup,
        channel_label=html.escape(view.title()),
        badge_label=html.escape(badge_label),
        title=title,
        meta=meta,
        price=html.escape(price_label),
        promise_label=html.escape(promise_label),
        details_markup="".join(details),
    )

    button_label = str(gallery_card_config.get("open_button_label_key", "ui.open_images") or "ui.open_images")
    slideshow_key = f"open_slideshow_{view}_{return_route}_{card_context}_{product.get('product_id', '')}"
    st.markdown("<div class='mt-catalog-actions'>", unsafe_allow_html=True)
    if view == "marketplace":
        action_cols = st.columns([1.2, 1, 1], gap="small")
        if action_cols[0].button(
            f"{t(button_label)} ({image_badge})",
            key=slideshow_key,
            use_container_width=True,
            disabled=not bool(images),
        ):
            open_slideshow(
                product_id=product.get("product_id", ""),
                return_route=return_route,
                slideshow_context=f"{view}_{return_route}_{card_context}",
            )
            st.rerun()
        if action_cols[1].button(t("action.add_to_cart"), key=f"marketplace_{product.get('product_id', '')}_cart", use_container_width=True) and on_add_to_cart:
            on_add_to_cart(product)
        if action_cols[2].button("Buy Now", key=f"marketplace_{product.get('product_id', '')}_buy", use_container_width=True):
            if on_buy_now:
                on_buy_now(product)
            elif on_add_to_cart:
                on_add_to_cart(product)
    elif view == "manditrade":
        action_cols = st.columns([1.25, 1], gap="small")
        if action_cols[0].button(
            f"{t(button_label)} ({image_badge})",
            key=slideshow_key,
            use_container_width=True,
            disabled=not bool(images),
        ):
            open_slideshow(
                product_id=product.get("product_id", ""),
                return_route=return_route,
                slideshow_context=f"{view}_{return_route}_{card_context}",
            )
            st.rerun()
        if action_cols[1].button(t("ui.request_order"), key=f"manditrade_{product.get('product_id', '')}_request", use_container_width=True) and on_add_to_cart:
            on_add_to_cart(product)
    else:
        if st.button(
            f"{t(button_label)} ({image_badge})",
            key=slideshow_key,
            use_container_width=True,
            disabled=not bool(images),
        ):
            open_slideshow(
                product_id=product.get("product_id", ""),
                return_route=return_route,
                slideshow_context=f"{view}_{return_route}_{card_context}",
            )
            st.rerun()
    if merchant_upi_link and view == "marketplace":
        st.markdown(
            f"<div class='mt-catalog-card__upi-link'><a href='{html.escape(merchant_upi_link, quote=True)}'>Merchant payment link</a></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
