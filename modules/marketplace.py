from __future__ import annotations

import streamlit as st

from components.product_grid import render_product_grid


def _matches_search(product: dict, query: str) -> bool:
    haystack = " ".join(
        [
            str(product.get("product_name", "")),
            str(product.get("product_code", "")),
            str(product.get("category", "")),
            str(product.get("subcategory", "")),
            str(product.get("description", "")),
        ]
    ).lower()
    return query in haystack


def render_marketplace_page(products: list[dict], on_add_to_cart, media_service=None, translator=None) -> None:
    query = st.text_input(
        f"{translator.t('action.search') if translator else 'Search'} {translator.t('module.marketplace.title') if translator else 'Marketplace'}",
        key="marketplace_search",
    ).strip().lower()
    marketplace_products = [
        product
        for product in products
        if ((product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled")
        and str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"
        and (not query or _matches_search(product, query))
    ]
    render_product_grid(
        marketplace_products,
        view="marketplace",
        on_add_to_cart=on_add_to_cart,
        media_service=media_service,
        return_route="marketplace",
        grid_context="marketplace_grid",
    )
