from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class ProductCatalogService:
    def __init__(self, governance_service, id_allocator_service) -> None:
        self.governance_service = governance_service
        self.id_allocator_service = id_allocator_service

    def list_products(
        self,
        *,
        include_pending: bool = True,
        viewer_role: str | None = None,
        viewer_code: str | None = None,
    ) -> list[dict[str, Any]]:
        products = self.governance_service.list_products()
        active_visible_products = [
            item for item in products if item.get("status") == "ACTIVE" and item.get("visible", True)
        ]
        if viewer_role == "platform_admin":
            return products if include_pending else active_visible_products
        if viewer_role in {"manufacturer", "admin_as_manufacturer"}:
            return [
                item
                for item in products
                if (item.get("status") == "ACTIVE" and item.get("visible", True))
                or (viewer_code and item.get("created_by") == viewer_code)
            ]
        return active_visible_products

    def propose_product(self, *, created_by: str, name: str, category: str, unit: str) -> dict[str, Any]:
        product = {
            "product_id": self.id_allocator_service.allocate("product"),
            "name": name.strip(),
            "category": category.strip(),
            "unit": unit.strip(),
            "mandi_price": 0,
            "mrp": 0,
            "status": "PROPOSED",
            "created_by": created_by,
            "approved_by": "",
            "created_at": datetime.now(UTC).isoformat(),
            "approved_at": "",
            "visible": False,
        }
        self.governance_service.upsert_product(product)
        return product

    def approve_product(
        self,
        *,
        product_id: str,
        approved_by: str,
        mandi_price: float,
        mrp: float,
        category: str | None = None,
        unit: str | None = None,
        visible: bool = True,
    ) -> dict[str, Any]:
        products = self.governance_service.list_products()
        product = next((item for item in products if item.get("product_id") == product_id), None)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        product.update(
            {
                "mandi_price": float(mandi_price),
                "mrp": float(mrp),
                "status": "ACTIVE",
                "approved_by": approved_by,
                "approved_at": datetime.now(UTC).isoformat(),
                "category": (category or product.get("category", "")).strip(),
                "unit": (unit or product.get("unit", "")).strip(),
                "visible": bool(visible),
            }
        )
        self.governance_service.upsert_product(product)
        return product

    def reject_product(self, *, product_id: str, approved_by: str) -> dict[str, Any]:
        products = self.governance_service.list_products()
        product = next((item for item in products if item.get("product_id") == product_id), None)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        product.update(
            {
                "status": "REJECTED",
                "approved_by": approved_by,
                "approved_at": datetime.now(UTC).isoformat(),
                "visible": False,
            }
        )
        self.governance_service.upsert_product(product)
        return product
