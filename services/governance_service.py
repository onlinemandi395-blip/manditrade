from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.json_service import JsonService


class GovernanceService:
    def __init__(self, governance_root: Path, safe_drive_write_service) -> None:
        self.governance_root = governance_root
        self.json_service = JsonService()
        self.safe_drive_write_service = safe_drive_write_service

    @property
    def products_path(self) -> Path:
        return self.governance_root / "products.json"

    @property
    def manufacturers_path(self) -> Path:
        return self.governance_root / "manufacturers.json"

    def ensure_files(self) -> None:
        if not self.products_path.exists():
            self.safe_drive_write_service.replace_document(
                self.products_path,
                {"schema_version": "1.0", "products": []},
                schema_name="products",
            )
        if not self.manufacturers_path.exists():
            self.safe_drive_write_service.replace_document(
                self.manufacturers_path,
                {"schema_version": "1.0", "manufacturers": []},
                schema_name="manufacturers",
            )

    def list_products(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.products_path, {"products": []}).get("products", [])

    def upsert_product(self, product: dict[str, Any]) -> None:
        self.ensure_files()
        payload = self.json_service.read_json(self.products_path, {"products": []})
        products = payload.get("products", [])
        existing = next((item for item in products if item["product_code"] == product["product_code"]), None)
        if existing:
            existing.update(product)
        else:
            products.append(product)
        payload["products"] = products
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.products_path, payload, schema_name="products")

    def list_manufacturers(self) -> list[dict[str, Any]]:
        self.ensure_files()
        return self.json_service.read_json(self.manufacturers_path, {"manufacturers": []}).get("manufacturers", [])

    def register_manufacturer(self, manufacturer: dict[str, Any]) -> None:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        manufacturers = payload.get("manufacturers", [])
        existing = next(
            (item for item in manufacturers if item["manufacturer_code"] == manufacturer["manufacturer_code"]),
            None,
        )
        if existing:
            existing.update(manufacturer)
        else:
            manufacturers.append(manufacturer)
        payload["manufacturers"] = manufacturers
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")

    def get_manufacturer(self, manufacturer_code: str) -> dict[str, Any] | None:
        self.ensure_files()
        manufacturers = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []}).get("manufacturers", [])
        return next((item for item in manufacturers if item.get("manufacturer_code") == manufacturer_code), None)

    def update_manufacturer(self, manufacturer_code: str, updates: dict[str, Any]) -> dict[str, Any]:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        updated: dict[str, Any] | None = None
        for item in payload.get("manufacturers", []):
            if item.get("manufacturer_code") == manufacturer_code:
                item.update(updates)
                item["updated_at"] = datetime.now(UTC).isoformat()
                updated = dict(item)
                break
        if updated is None:
            raise ValueError(f"Manufacturer not found: {manufacturer_code}")
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")
        return updated

    def delete_manufacturer(self, manufacturer_code: str) -> bool:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        original_count = len(payload.get("manufacturers", []))
        payload["manufacturers"] = [item for item in payload.get("manufacturers", []) if item.get("manufacturer_code") != manufacturer_code]
        if len(payload["manufacturers"]) == original_count:
            return False
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")
        return True

    def update_manufacturer_status(self, manufacturer_code: str, status: str, subscription_plan: str | None = None) -> None:
        self.ensure_files()
        payload = self.json_service.read_json(self.manufacturers_path, {"manufacturers": []})
        for item in payload.get("manufacturers", []):
            if item["manufacturer_code"] == manufacturer_code:
                item["status"] = status
                if subscription_plan:
                    item["subscription_plan"] = subscription_plan
        payload.setdefault("schema_version", "1.0")
        self.safe_drive_write_service.replace_document(self.manufacturers_path, payload, schema_name="manufacturers")
