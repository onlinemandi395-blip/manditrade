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
            "roles": self.config_loader_service.load("roles"),
            "users": self.config_loader_service.load("users"),
            "navigation": self.config_loader_service.load("navigation"),
            "modules": self.config_loader_service.load("modules"),
            "dashboards": self.config_loader_service.load("dashboards"),
            "forms": self.config_loader_service.load("forms"),
            "workflows": self.config_loader_service.load("workflows"),
            "actions": self.config_loader_service.load("actions"),
            "notifications": self.config_loader_service.load("notifications"),
            "database": self.config_loader_service.load("database"),
            "theme": self.config_loader_service.load("theme"),
            "product_mapping": self.config_loader_service.load("product_mapping"),
            "seed_data": self.config_loader_service.load("seed_data"),
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
