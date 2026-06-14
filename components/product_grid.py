from __future__ import annotations

import streamlit as st

from components.image_slideshow import SLIDESHOW_CONTEXT_KEY, SLIDESHOW_PRODUCT_KEY, is_slideshow_active, render_image_slideshow
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
    ui_config: dict | None = None,
) -> None:
    slideshow_context = f"{view}_{return_route}_{grid_context}"
    if is_slideshow_active():
        active_product_id = str(st.session_state.get(SLIDESHOW_PRODUCT_KEY, "") or "").strip()
        active_context = str(st.session_state.get(SLIDESHOW_CONTEXT_KEY, "") or "").strip()
        active_product = next((product for product in products if str(product.get("product_id", "")).strip() == active_product_id), None)
        if active_context == slideshow_context and active_product and media_service is not None:
            try:
                render_image_slideshow(
                    active_product,
                    media_service=media_service,
                    view=view,
                    translator=translator,
                    ui_config=ui_config,
                    slideshow_context=slideshow_context,
                )
            except Exception as exc:
                st.error(f"Unable to open product slideshow: {exc}")
            return
    if not products:
        render_empty_state(translator.t("ui.no_products_found") if translator else "No products found.")
        return
    desktop_columns = 4
    for row_start in range(0, len(products), desktop_columns):
        row_products = products[row_start:row_start + desktop_columns]
        st.markdown("<div class='mt-product-grid-row'></div>", unsafe_allow_html=True)
        columns = st.columns(desktop_columns, gap="small")
        for column_index, column in enumerate(columns):
            if column_index >= len(row_products):
                continue
            product = row_products[column_index]
            with column:
                render_product_card(
                    product,
                    view=view,
                    on_add_to_cart=on_add_to_cart if view == "marketplace" else on_request,
                    media_service=media_service,
                    return_route=return_route,
                    card_context=f"{grid_context}_{row_start + column_index}",
                    translator=translator,
                    ui_config=ui_config,
                )
