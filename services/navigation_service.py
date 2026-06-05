from __future__ import annotations


class NavigationService:
    def __init__(self, cache_service, translator, rbac_service) -> None:
        self.cache_service = cache_service
        self.translator = translator
        self.rbac_service = rbac_service

    def get_navigation(self, role: str) -> list[dict]:
        navigation_config = self.cache_service.get_config("navigation")
        rows = navigation_config.get("navigation", {}).get("items", [])
        visible_items = []
        for item in rows:
            route = str(item.get("route", ""))
            if route and self.rbac_service.can_access(role, route):
                visible_items.append(
                    {
                        **item,
                        "label": self.translator.t(item.get("label_key", route)),
                    }
                )
        return visible_items

    def get_default_route(self, role: str) -> str:
        role_views = self.cache_service.get_config("role_views").get("role_views", {})
        route = str(role_views.get(role, {}).get("landing_page", ""))
        if route and self.rbac_service.can_access(role, route):
            return route
        navigation_items = self.get_navigation(role)
        if navigation_items:
            return str(navigation_items[0].get("route", "dashboard"))
        return "dashboard"
