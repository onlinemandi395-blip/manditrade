from __future__ import annotations

from components.commerce_catalog import render_commerce_catalog_page


def render_manditrade_page(products: list[dict], on_request=None, media_service=None, translator=None, ui_config: dict | None = None) -> None:
    render_commerce_catalog_page(
        products,
        route="manditrade",
        channel="manditrade",
        price_key="manditrade_price",
        placeholder="Search for bulk products, categories, brands...",
        grid_context="manditrade_grid",
        on_request=on_request,
        media_service=media_service,
        translator=translator,
        ui_config=ui_config,
    )
