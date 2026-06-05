from __future__ import annotations

from components.product_grid import render_product_grid


def render_marketplace_page(products: list[dict], on_add_to_cart) -> None:
    marketplace_products = [
        product
        for product in products
        if ((product.get("sales_channels") or {}).get("marketplace") or {}).get("enabled")
    ]
    render_product_grid(marketplace_products, view="marketplace", on_add_to_cart=on_add_to_cart)
