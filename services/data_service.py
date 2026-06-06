from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import streamlit as st

from services.id_service import IdService


class DataService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service
        self.id_service = IdService()
        st.session_state.setdefault("mt_next_data", {})

    def _bootstrap_collection(self, collection: str) -> list[dict]:
        cache_data = st.session_state["mt_next_data"]
        if collection in cache_data:
            return cache_data[collection]
        database_config = self.cache_service.get_config("database")
        source = database_config.get("collections", {}).get(collection, "")
        if not source:
            raise KeyError(f"No Drive collection mapping configured for: {collection}")
        payload = []
        if ":" in source:
            config_name, key = source.split(":", 1)
            payload = deepcopy(self.cache_service.get_config(config_name).get(key, []))
        else:
            raise ValueError(f"Invalid Drive collection mapping for: {collection}")
        if collection == "products":
            payload = [self.normalize_product_record(item) for item in payload]
        cache_data[collection] = payload
        return cache_data[collection]

    def list_collection(self, collection: str) -> list[dict]:
        return list(self._bootstrap_collection(collection))

    def get_collection_ref(self, collection: str) -> list[dict]:
        return self._bootstrap_collection(collection)

    def create_record(self, collection: str, values: dict) -> dict:
        rows = self._bootstrap_collection(collection)
        record = dict(values)
        record["id"] = self.id_service.next(collection.rstrip("s") or "record")
        record["created_at"] = datetime.now(UTC).isoformat()
        rows.append(record)
        return record

    def normalize_product_record(self, record: dict) -> dict:
        product = deepcopy(record)
        product.setdefault("product_id", self.id_service.next("product"))
        product.setdefault("product_code", product.get("product_id", ""))
        product.setdefault("product_name", "")
        product.setdefault("status", "ACTIVE")
        product.setdefault("category", "General")
        product.setdefault("subcategory", "")
        product.setdefault("description", "")
        product.setdefault("unit", "piece")
        if not product.get("image_url"):
            for image in product.get("images", []) or []:
                product["image_url"] = image.get("thumbnail_url") or image.get("view_url") or ""
                if product["image_url"]:
                    break
        sales_channels = dict(product.get("sales_channels", {}) or {})
        if "mandiplace" in sales_channels and "manditrade" not in sales_channels:
            sales_channels["manditrade"] = sales_channels.pop("mandiplace")
        sales_channels.pop("suta_mandi", None)
        sales_channels.setdefault("marketplace", {"enabled": False, "price": 0})
        sales_channels.setdefault("manditrade", {"enabled": False, "price": 0})
        product["sales_channels"] = sales_channels
        manufacturer_tags = product.get("manufacturer_tags")
        if manufacturer_tags is None:
            manufacturer_tags = []
            for item in product.get("manufacturer_mapping", []) or []:
                manufacturer_tags.append(
                    {
                        "email": ((item.get("contact") or {}).get("email", "")),
                        "manufacturer_id": item.get("manufacturer_id", ""),
                        "name": item.get("manufacturer_name", ""),
                        "priority": item.get("priority", 1),
                        "active": item.get("active", True),
                    }
                )
        mahajan_tags = product.get("mahajan_tags")
        if mahajan_tags is None:
            mahajan_tags = []
            for item in product.get("mahajan_mapping", []) or []:
                mahajan_tags.append(
                    {
                        "email": ((item.get("contact") or {}).get("email", "")),
                        "mahajan_id": item.get("mahajan_id", ""),
                        "name": item.get("mahajan_name", ""),
                        "raw_materials": item.get("supplied_raw_materials", []),
                        "active": item.get("active", True),
                    }
                )
        product["manufacturer_tags"] = manufacturer_tags
        product["mahajan_tags"] = mahajan_tags
        inventory = dict(product.get("inventory", {}) or {})
        if not inventory and product.get("manufacturer_mapping"):
            first_mapping = (product.get("manufacturer_mapping") or [{}])[0]
            inventory = dict(first_mapping.get("inventory", {}) or {})
        inventory.setdefault("available_quantity", 0)
        inventory.setdefault("unit", product.get("unit", "piece"))
        product["inventory"] = inventory
        product["created_at"] = product.get("created_at") or datetime.now(UTC).isoformat()
        product["updated_at"] = product.get("updated_at") or product["created_at"]
        return product
