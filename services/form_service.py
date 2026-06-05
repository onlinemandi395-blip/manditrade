from __future__ import annotations


class FormService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service

    def get_form(self, form_id: str) -> dict:
        return self.cache_service.get_config("forms").get("forms", {}).get(form_id, {})
