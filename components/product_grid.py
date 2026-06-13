from __future__ import annotations

import streamlit as st

from components.image_slideshow import SLIDESHOW_PRODUCT_KEY, is_slideshow_active, render_image_slideshow
from components.product_card import render_product_card
from components.empty_state import render_empty_state


def render_product_grid(
    products: list[dict],
    *,
    view: str = "marketplace",
    on_add_to_cart=None,
    on_request=None,
    media_service=None,
    return_route: str = "",
    grid_context: str = "",
    translator=None,
) -> None:
    if is_slideshow_active():
        active_product_id = str(st.session_state.get(SLIDESHOW_PRODUCT_KEY, "") or "").strip()
        active_product = next((product for product in products if str(product.get("product_id", "")).strip() == active_product_id), None)
        if active_product and media_service is not None:
            render_image_slideshow(active_product, media_service=media_service, view=view)
            return
    if not products:
      render_empty_state(translator.t("ui.no_products_found") if translator else "No products found.")
      return
    columns = st.columns(3)
    for index, product in enumerate(products):
        with columns[index % 3]:
            render_product_card(
                product,
                view=view,
                on_add_to_cart=on_add_to_cart if view == "marketplace" else on_request,
                media_service=media_service,
                return_route=return_route,
                card_context=f"{grid_context}_{index}",
                translator=translator,
            )
