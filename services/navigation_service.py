from __future__ import annotations

from services.auth_service import is_bootstrap_admin, normalize_role


class NavigationService:
    ESSENTIAL_ITEMS = [
        {"route": "payments", "icon": "[PY]", "label_key": "sidebar.payments"},
        {"route": "ledger", "icon": "[LG]", "label_key": "sidebar.ledger"},
        {"route": "completed_deliveries", "icon": "[CD]", "label_key": "sidebar.completed_deliveries"},
    ]

    def __init__(self, cache_service, translator, rbac_service) -> None:
        self.cache_service = cache_service
        self.translator = translator
        self.rbac_service = rbac_service

    def _get_navigation_rows(self) -> list[dict]:
        navigation_config = self.cache_service.get_config("navigation")
        rows = list(navigation_config.get("navigation", {}).get("items", []) or [])
        existing_routes = {str(item.get("route", "")).strip() for item in rows if str(item.get("route", "")).strip()}
        for item in self.ESSENTIAL_ITEMS:
            route = str(item.get("route", "")).strip()
            if route and route not in existing_routes:
                rows.append(dict(item))
        return rows

    def _get_admin_allowed_routes(self, role: str, user: dict | None = None) -> list[str]:
        if normalize_role(role) != "platform_admin" or not isinstance(user, dict):
            return []
        if is_bootstrap_admin(str(user.get("email", "") or "").strip().lower()):
            return []
        configured_routes = user.get("admin_navigation_routes", []) or []
        if isinstance(configured_routes, str):
            configured_routes = [configured_routes]
        return [
            str(route).strip()
            for route in configured_routes
            if str(route).strip()
        ]

    def get_navigation(self, role: str, user: dict | None = None) -> list[dict]:
        role = normalize_role(role)
        rows = self._get_navigation_rows()
        restricted_routes = set(self._get_admin_allowed_routes(role, user))
        visible_items = []
        for item in rows:
            route = str(item.get("route", ""))
            if route and self.rbac_service.can_access(role, route):
                if restricted_routes and route not in restricted_routes:
                    continue
                visible_items.append(
                    {
                        **item,
                        "label": self.translator.t(item.get("label_key", route)),
                    }
                )
        return visible_items

    def get_default_route(self, role: str, user: dict | None = None) -> str:
        role = normalize_role(role)
        role_views = self.cache_service.get_config("role_views").get("role_views", {})
        route = str(role_views.get(role, {}).get("landing_page", ""))
        allowed_routes = set(self._get_admin_allowed_routes(role, user))
        if route and self.rbac_service.can_access(role, route) and (not allowed_routes or route in allowed_routes):
            return route
        navigation_items = self.get_navigation(role, user=user)
        if navigation_items:
            return str(navigation_items[0].get("route", "dashboard"))
        return "dashboard"
