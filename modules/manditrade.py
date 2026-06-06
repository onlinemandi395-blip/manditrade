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


def render_manditrade_page(products: list[dict], on_request=None, media_service=None, translator=None) -> None:
    query = st.text_input(
        f"{translator.t('action.search') if translator else 'Search'} {translator.t('module.manditrade.title') if translator else 'MandiTrade'}",
        key="manditrade_search",
    ).strip().lower()
    manditrade_products = [
        product
        for product in products
        if ((product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled")
        and str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"
        and (not query or _matches_search(product, query))
    ]
    render_product_grid(manditrade_products, view="manditrade", on_request=on_request, media_service=media_service)
