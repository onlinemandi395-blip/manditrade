from __future__ import annotations


class NavigationService:
    def __init__(self, cache_service, translator, rbac_service) -> None:
        self.cache_service = cache_service
        self.translator = translator
        self.rbac_service = rbac_service

    def get_navigation(self, role: str) -> list[dict]:
        rows = self.cache_service.get_config("navigation").get("navigation", {}).get(role, [])
        return [
            {
                **item,
                "label": self.translator.t(item.get("label_key", item.get("route", ""))),
            }
            for item in rows
        ]

    def get_default_route(self, role: str) -> str:
        app_config = self.cache_service.get_config("app_config")
        return str(app_config.get("default_landing", {}).get(role, app_config.get("default_role", "public_buyer")))
