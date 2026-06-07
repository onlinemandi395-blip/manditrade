from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import streamlit as st

from services.admin_drive_service import AdminDriveService
from services.id_service import IdService
from services.performance_service import PerformanceService


class DataService:
    DEFAULT_COLLECTION_MAPPINGS = {
        "users": "users:users",
        "products": "products_data:products",
        "orders": "orders_data:orders",
        "payments": "payments_data:payments",
        "shipments": "shipments_data:shipments",
        "ledger": "ledger_data:ledger",
        "notifications": "notifications_data:notifications",
        "gmail_queue": "gmail_queue_data:gmail_queue",
    }

    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service
        self.id_service = IdService()
        self.admin_drive_service = AdminDriveService()
        self.performance_service = PerformanceService()
        st.session_state.setdefault("mt_next_data", {})

    def _bootstrap_collection(self, collection: str) -> list[dict]:
        cache_data = st.session_state["mt_next_data"]
        if collection in cache_data:
            return cache_data[collection]
        database_config = self.cache_service.get_config("database")
        source = database_config.get("collections", {}).get(collection, "") or self.DEFAULT_COLLECTION_MAPPINGS.get(collection, "")
        if not source:
            raise KeyError(f"No Drive collection mapping configured for: {collection}")
        payload = []
        if ":" in source:
            config_name, key = source.split(":", 1)
            with self.performance_service.measure(f"{collection}_list_load"):
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

    def persist_collection(self, collection: str) -> None:
        database_config = self.cache_service.get_config("database")
        source = database_config.get("collections", {}).get(collection, "") or self.DEFAULT_COLLECTION_MAPPINGS.get(collection, "")
        if ":" not in source:
            raise ValueError(f"Invalid Drive collection mapping for: {collection}")
        config_name, key = source.split(":", 1)
        collection_rows = self._bootstrap_collection(collection)
        logical_path_map = {
            "users": "01_identity/users.json",
            "products_data": "02_catalog/products.json",
            "orders_data": "05_orders/orders.json",
            "payments_data": "07_ledger/payments.json",
            "shipments_data": "06_shipments/shipments.json",
            "ledger_data": "07_ledger/ledger.json",
            "notifications_data": "09_notifications/notifications.json",
            "gmail_queue_data": "09_notifications/gmail_queue.json",
        }
        logical_path = logical_path_map.get(config_name)
        if not logical_path:
            raise KeyError(f"No Drive file path configured for collection source: {config_name}")
        payload = {"schema_version": 1, key: collection_rows}
        with self.performance_service.measure(f"{collection}_save"):
            self.admin_drive_service.write_json(logical_path, payload)
        self.cache_service.update_config(config_name, payload)

    def normalize_product_record(self, record: dict) -> dict:
        product = deepcopy(record)
        product.setdefault("product_id", self.id_service.next("product"))
        product.setdefault("product_code", product.get("product_id", ""))
        product.setdefault("product_name", "")
        raw_status = str(product.get("status", "APPROVED") or "APPROVED").strip().upper()
        if raw_status == "ACTIVE":
            raw_status = "APPROVED"
        product["status"] = raw_status
        product.setdefault("category", "General")
        product.setdefault("subcategory", "")
        product.setdefault("description", "")
        product.setdefault("unit", "piece")
        images = [dict(image or {}) for image in (product.get("images", []) or [])]
        for image in images:
            if not image.get("direct_render_url") and image.get("file_id"):
                image["direct_render_url"] = f"https://drive.google.com/uc?export=view&id={image.get('file_id', '')}"
            if not image.get("web_content_link") and image.get("file_id"):
                image["web_content_link"] = f"https://drive.google.com/uc?export=download&id={image.get('file_id', '')}"
        product["images"] = images
        primary_image = next((image for image in images if image.get("is_primary")), images[0] if images else {})
        if not product.get("image_url"):
            product["image_url"] = (
                primary_image.get("direct_render_url")
                or primary_image.get("image_url")
                or primary_image.get("thumbnail_link")
                or primary_image.get("web_content_link")
                or primary_image.get("web_view_link")
                or ""
            )
        sales_channels = dict(product.get("sales_channels", {}) or {})
        if "mandiplace" in sales_channels and "manditrade" not in sales_channels:
            sales_channels["manditrade"] = sales_channels.pop("mandiplace")
        sales_channels.pop("suta_mandi", None)
        marketplace_channel = dict(sales_channels.get("marketplace", {}) or {})
        manditrade_channel = dict(sales_channels.get("manditrade", {}) or {})
        pricing = dict(product.get("pricing", {}) or {})
        pricing.setdefault("admin_price", 0)
        pricing.setdefault("marketplace_price", marketplace_channel.get("price", 0))
        pricing.setdefault("manditrade_price", manditrade_channel.get("price", 0))
        pricing.setdefault("currency", "INR")
        sales_channels["marketplace"] = {"enabled": bool(marketplace_channel.get("enabled", False))}
        sales_channels["manditrade"] = {"enabled": bool(manditrade_channel.get("enabled", False))}
        product["sales_channels"] = sales_channels
        product["pricing"] = pricing
        owner = dict(product.get("owner", {}) or {})
        if not owner:
            if product.get("manufacturer"):
                manufacturer = dict(product.get("manufacturer", {}) or {})
                owner = {
                    "email": manufacturer.get("email", ""),
                    "role": "manufacturer",
                    "display_name": manufacturer.get("name", ""),
                    "user_id": manufacturer.get("manufacturer_id", ""),
                }
            elif product.get("mahajan"):
                mahajan = dict(product.get("mahajan", {}) or {})
                owner = {
                    "email": mahajan.get("email", ""),
                    "role": "mahajan",
                    "display_name": mahajan.get("name", ""),
                    "user_id": mahajan.get("mahajan_id", ""),
                }
            else:
                legacy_manufacturers = product.get("manufacturer_tags") or []
                legacy_mahajans = product.get("mahajan_tags") or []
                if legacy_manufacturers:
                    first_owner = legacy_manufacturers[0]
                    owner = {
                        "email": first_owner.get("email", ""),
                        "role": "manufacturer",
                        "display_name": first_owner.get("name", ""),
                        "user_id": first_owner.get("manufacturer_id", ""),
                    }
                elif legacy_mahajans:
                    first_owner = legacy_mahajans[0]
                    owner = {
                        "email": first_owner.get("email", ""),
                        "role": "mahajan",
                        "display_name": first_owner.get("name", ""),
                        "user_id": first_owner.get("mahajan_id", ""),
                    }
        product["owner"] = owner
        delivery_partner = dict(product.get("delivery_partner", {}) or {})
        product["delivery_partner"] = {
            "email": str(delivery_partner.get("email", "")).strip().lower(),
            "role": "delivery_partner" if str(delivery_partner.get("email", "")).strip() else "",
            "display_name": str(delivery_partner.get("display_name", "")).strip(),
            "user_id": str(delivery_partner.get("user_id", "")).strip(),
            "phone": str(delivery_partner.get("phone", "")).strip(),
        }
        product.pop("manufacturer_tags", None)
        product.pop("mahajan_tags", None)
        product.pop("manufacturer_mapping", None)
        product.pop("mahajan_mapping", None)
        product.pop("manufacturer", None)
        product.pop("mahajan", None)
        inventory = dict(product.get("inventory", {}) or {})
        inventory.setdefault("available_quantity", 0)
        inventory.setdefault("manual_update_only", True)
        product["inventory"] = inventory
        approval = dict(product.get("approval", {}) or {})
        approval.setdefault("submitted_by", product.get("created_by", ""))
        approval.setdefault("submitted_at", product.get("created_at", ""))
        approval.setdefault("approved_by", "")
        approval.setdefault("approved_at", "")
        approval.setdefault("rejected_by", "")
        approval.setdefault("rejected_at", "")
        approval.setdefault("rejection_reason", "")
        if product["status"] == "APPROVED" and not approval.get("approved_at"):
            approval["approved_at"] = product.get("updated_at") or product.get("created_at") or datetime.now(UTC).isoformat()
        product["approval"] = approval
        product["created_at"] = product.get("created_at") or datetime.now(UTC).isoformat()
        product["updated_at"] = product.get("updated_at") or product["created_at"]
        product["created_by"] = product.get("created_by", "")
        product["updated_by"] = product.get("updated_by", "")
        return product

    def upsert_user(self, user_record: dict) -> dict:
        users = self.get_collection_ref("users")
        email = str(user_record.get("email", "")).strip().lower()
        existing = next((user for user in users if str(user.get("email", "")).strip().lower() == email), None)
        if existing:
            existing.update(user_record)
            return existing
        users.append(user_record)
        return user_record
