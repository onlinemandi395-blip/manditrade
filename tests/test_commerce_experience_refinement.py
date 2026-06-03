from __future__ import annotations

from pathlib import Path

from modules.marketplace.dashboard import filter_marketplace_products
from services.trust_badge_service import TrustBadgeService


def test_marketplace_filter_supports_category_price_and_sort():
    products = [
        {"product_id": "PRD-1", "name": "Rice Premium", "category": "Grain", "approved_marketplace_price": 50, "visible": True, "minimum_order_qty": 2, "created_at": "2026-06-01T00:00:00+00:00"},
        {"product_id": "PRD-2", "name": "Masala Mix", "category": "Spices", "approved_marketplace_price": 80, "visible": True, "minimum_order_qty": 1, "created_at": "2026-06-03T00:00:00+00:00"},
        {"product_id": "PRD-3", "name": "Rice Value", "category": "Grain", "approved_marketplace_price": 40, "visible": True, "minimum_order_qty": 1, "created_at": "2026-05-31T00:00:00+00:00"},
    ]

    filtered = filter_marketplace_products(
        products,
        search_term="rice",
        category_filter="Grain",
        max_price=45,
        in_stock_only=True,
        sort_by="Price: Low to High",
    )

    assert [item["product_id"] for item in filtered] == ["PRD-3"]


def test_trust_badges_expand_for_marketplace_and_raw_material():
    service = TrustBadgeService()

    marketplace_badges = service.badges_for_marketplace_product(
        {
            "approved_visibility": "PUBLIC",
            "available_for_public_sale": True,
            "minimum_order_qty": 1,
            "ratings": [{"rating": 5}],
            "public_seller_manufacturer_id": "MANU101",
            "status": "ACTIVE",
        }
    )
    raw_material_badges = service.badges_for_raw_material(
        {
            "available_qty": 75,
            "category": "SUTA",
            "mahajan_id": "MAH001",
            "ratings": [{"rating": 4}],
        }
    )

    assert "Public Catalog" in marketplace_badges
    assert "Low MOQ" in marketplace_badges
    assert "Available Now" in raw_material_badges
    assert "Yarn Specialist" in raw_material_badges


def test_marketplace_source_contains_cart_controls_and_detail_drawer():
    content = Path("modules/marketplace/dashboard.py").read_text(encoding="utf-8")

    assert "render_catalog_detail_drawer" in content
    assert "cart_service.update_qty" in content
    assert "cart_service.remove_item" in content
    assert "Estimated delivery: seller dispatch after payment verification." in content


def test_suta_and_raw_material_sources_render_commerce_detail_layers():
    suta_content = Path("modules/suta_mandi/dashboard.py").read_text(encoding="utf-8")
    raw_content = Path("modules/raw_materials/dashboard.py").read_text(encoding="utf-8")

    assert "render_catalog_detail_drawer" in suta_content
    assert "MOQ" in suta_content
    assert "render_catalog_detail_drawer" in raw_content
    assert "Procurement" in raw_content
