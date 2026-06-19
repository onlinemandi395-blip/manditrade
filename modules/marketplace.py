from __future__ import annotations

from components.commerce_catalog import render_commerce_catalog_page


def render_marketplace_page(products: list[dict], on_add_to_cart, media_service=None, translator=None, ui_config: dict | None = None) -> None:
    render_commerce_catalog_page(
        products,
        route="marketplace",
        channel="marketplace",
        price_key="marketplace_price",
        placeholder="Search for products, categories, brands...",
        grid_context="marketplace_grid",
        on_add_to_cart=on_add_to_cart,
        media_service=media_service,
        translator=translator,
        ui_config=ui_config,
    )
