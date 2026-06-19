from __future__ import annotations

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


def _sort_products(products: list[dict], sort_by: str, *, price_key: str) -> list[dict]:
    if sort_by == "Price Low to High":
        return sorted(products, key=lambda row: float(((row.get("pricing") or {}).get(price_key, 0)) or 0))
    if sort_by == "Price High to Low":
        return sorted(products, key=lambda row: float(((row.get("pricing") or {}).get(price_key, 0)) or 0), reverse=True)
    if sort_by == "Newest":
        return sorted(products, key=lambda row: str(row.get("created_at", "") or ""), reverse=True)
    return products


def render_commerce_catalog_page(
    products: list[dict],
    *,
    route: str,
    channel: str,
    price_key: str,
    placeholder: str,
    grid_context: str,
    media_service=None,
    translator=None,
    ui_config: dict | None = None,
    on_add_to_cart=None,
    on_request=None,
) -> None:
    render_template("commerce_shell_open.html")
    query = render_commerce_search(route=route, placeholder=placeholder)
    categories = sorted({str(product.get("category", "")).strip() for product in products if str(product.get("category", "")).strip()})
    selected_category = render_category_strip(route=route, categories=categories, selected_category="All")
    render_template("commerce_toolbar_open.html")
    filters = render_filter_bar(route=route)
    render_template("html_close_div.html")
    render_template("html_close_div.html")

    visible_products = [
        product
        for product in products
        if ((product.get("sales_channels") or {}).get(channel) or {}).get("enabled")
        and str(product.get("status", "PENDING_APPROVAL")).upper() == "APPROVED"
        and str(product.get("posting_status", "READY_TO_POST")).upper() == "READY_TO_POST"
        and (not query or _matches_search(product, query))
        and (selected_category == "All" or str(product.get("category", "")).strip() == selected_category)
        and (filters["availability"] == "All" or float(((product.get("inventory") or {}).get("available_quantity", 0) or 0)) > 0)
        and float(((product.get("pricing") or {}).get(price_key, 0)) or 0) >= filters["min_price"]
        and (filters["max_price"] <= 0 or float(((product.get("pricing") or {}).get(price_key, 0)) or 0) <= filters["max_price"])
    ]
    visible_products = _sort_products(visible_products, filters["sort_by"], price_key=price_key)
    render_product_grid(
        visible_products,
        view=channel,
        on_add_to_cart=on_add_to_cart,
        on_request=on_request,
        media_service=media_service,
        return_route=route,
        grid_context=grid_context,
        translator=translator,
        ui_config=ui_config,
    )
