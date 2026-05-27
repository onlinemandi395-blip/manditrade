from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class ProductCatalogService:
    def __init__(self, governance_service, id_allocator_service) -> None:
        self.governance_service = governance_service
        self.id_allocator_service = id_allocator_service

    def list_products(self, *, include_pending: bool = True) -> list[dict[str, Any]]:
        products = self.governance_service.list_products()
        if include_pending:
            return products
        return [item for item in products if item.get("status") == "ACTIVE"]

    def propose_product(self, *, created_by: str, name: str, category: str, unit: str) -> dict[str, Any]:
        product = {
            "product_id": self.id_allocator_service.allocate("product"),
            "name": name.strip(),
            "category": category.strip(),
            "unit": unit.strip(),
            "mandi_price": 0,
            "mrp": 0,
            "status": "PENDING_APPROVAL",
            "created_by": created_by,
            "approved_by": "",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.governance_service.upsert_product(product)
        return product

    def approve_product(self, *, product_id: str, approved_by: str, mandi_price: float, mrp: float) -> dict[str, Any]:
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
            }
        )
        self.governance_service.upsert_product(product)
        return product
