from __future__ import annotations


class PageService:
    def __init__(self, cache_service, translator, rbac_service) -> None:
        self.cache_service = cache_service
        self.translator = translator
        self.rbac_service = rbac_service

    def get_page_definition(self, route: str, role: str) -> dict:
        definition = self.cache_service.get_config("modules").get("modules", {}).get(route, {})
        if not definition:
            return {
                "type": "dashboard",
                "title_key": "module.dashboard.title",
                "subtitle_key": "module.dashboard.subtitle",
                "visible_to": [role],
            }
        if not self.rbac_service.can_access(role, route):
            return {
                "type": "dashboard",
                "title_key": "module.dashboard.title",
                "subtitle_key": "module.dashboard.subtitle",
                "visible_to": [role],
            }
        return definition

    def filter_rows(self, rows: list[dict], filters: dict) -> list[dict]:
        if not filters:
            return rows
        filtered = []
        for row in rows:
            include = True
            for dotted_key, expected in filters.items():
                value = row
                for key in dotted_key.split("."):
                    if isinstance(value, dict):
                        value = value.get(key)
                    else:
                        value = None
                        break
                if value != expected:
                    include = False
                    break
            if include:
                filtered.append(row)
        return filtered
