from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st


class CacheService:
    def __init__(self, config_loader_service) -> None:
        self.config_loader_service = config_loader_service
        self.cache_key = "mt_next_cache"

    def load_all_configs(self) -> dict:
        cache = {
            "app_config": self.config_loader_service.load("app_config"),
            "auth": self.config_loader_service.load("auth"),
            "permissions": self.config_loader_service.load("permissions"),
            "role_views": self.config_loader_service.load("role_views"),
            "users": self.config_loader_service.load("users"),
            "navigation": self.config_loader_service.load("navigation"),
            "modules": self.config_loader_service.load("modules"),
            "dashboards": self.config_loader_service.load("dashboards"),
            "forms": self.config_loader_service.load("forms"),
            "categories": self.config_loader_service.load("categories"),
            "database": self.config_loader_service.load("database"),
            "products_data": self.config_loader_service.load("products_data"),
            "orders_data": self.config_loader_service.load("orders_data"),
            "shipments_data": self.config_loader_service.load("shipments_data"),
            "ledger_data": self.config_loader_service.load("ledger_data"),
            "notifications_data": self.config_loader_service.load("notifications_data"),
            "gmail_queue_data": self.config_loader_service.load("gmail_queue_data"),
            "languages": {
                "en": self.config_loader_service.load_language("en"),
                "hi": self.config_loader_service.load_language("hi"),
                "mr": self.config_loader_service.load_language("mr"),
                "bn": self.config_loader_service.load_language("bn"),
            },
            "_loaded_at": datetime.now(UTC).isoformat(),
        }
        st.session_state[self.cache_key] = cache
        return cache

    def get_config(self, name: str):
        cache = st.session_state.get(self.cache_key)
        if not cache:
            cache = self.load_all_configs()
        return cache.get(name, {})

    def refresh_cache(self) -> dict:
        return self.load_all_configs()

    def get_cache_status(self) -> dict:
        cache = st.session_state.get(self.cache_key, {})
        return {
            "loaded": bool(cache),
            "keys": sorted(cache.keys()),
            "loaded_at": cache.get("_loaded_at", ""),
        }
