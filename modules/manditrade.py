from __future__ import annotations

from components.product_grid import render_product_grid


def render_manditrade_page(products: list[dict]) -> None:
    manditrade_products = [
        product
        for product in products
        if ((product.get("sales_channels") or {}).get("manditrade") or {}).get("enabled")
    ]
    render_product_grid(manditrade_products, view="manditrade")
