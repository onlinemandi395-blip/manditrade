from __future__ import annotations

import streamlit as st

from components.category_strip import render_category_strip
from components.commerce_search import render_commerce_search
from components.filter_bar import render_filter_bar
from components.html_renderer import render_template
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


def _sort_products(products: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "Price Low to High":
        return sorted(products, key=lambda row: float(((row.get("pricing") or {}).get("manditrade_price", 0)) or 0))
    if sort_by == "Price High to Low":
        return sorted(products, key=lambda row: float(((row.get("pricing") or {}).get("manditrade_price", 0)) or 0), reverse=True)
    if sort_by == "Newest":
        return sorted(products, key=lambda row: str(row.get("created_at", "") or ""), reverse=True)
    return products


def render_manditrade_page(products: list[dict], on_request=None, media_service=None, translator=None, ui_config: dict | None = None) -> None:
    render_template("commerce_shell_open.html")
    query = render_commerce_search(route="manditrade", placeholder="Search for bulk products, categories, brands...")
    categories = sorted({str(product.get("category", "")).strip() for product in products if str(product.get("category", "")).strip()})
    selected_category = render_category_strip(route="manditrade", categories=categories, selected_category="All")
    render_template("commerce_toolbar_open.html")
    filters = render_filter_bar(route="manditrade")
    render_template("html_close_div.html")
    render_template("html_close_div.html")
    manditrade_products = [
        product
        for product in products
        if ((product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled")
        and str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"
        and str(product.get("posting_status", "READY_TO_POST")).upper() == "READY_TO_POST"
        and (not query or _matches_search(product, query))
        and (selected_category == "All" or str(product.get("category", "")).strip() == selected_category)
        and (filters["availability"] == "All" or float(((product.get("inventory") or {}).get("available_quantity", 0) or 0)) > 0)
        and float(((product.get("pricing") or {}).get("manditrade_price", 0)) or 0) >= filters["min_price"]
        and (filters["max_price"] <= 0 or float(((product.get("pricing") or {}).get("manditrade_price", 0)) or 0) <= filters["max_price"])
    ]
    manditrade_products = _sort_products(manditrade_products, filters["sort_by"])
    render_product_grid(
        manditrade_products,
        view="manditrade",
        on_request=on_request,
        media_service=media_service,
        return_route="manditrade",
        grid_context="manditrade_grid",
        translator=translator,
        ui_config=ui_config,
    )
