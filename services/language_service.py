from __future__ import annotations


class Translator:
    def __init__(self, bundle: dict[str, str], fallback_bundle: dict[str, str] | None = None) -> None:
        self.bundle = bundle
        self.fallback_bundle = fallback_bundle or {}

    def t(self, key: str) -> str:
        return self.bundle.get(key, self.fallback_bundle.get(key, key))


class LanguageService:
    def __init__(self, cache_service, language_code: str) -> None:
        self.cache_service = cache_service
        self.language_code = language_code

    def get_translator(self) -> Translator:
        languages = self.cache_service.get_config("languages")
        bundle = languages.get(self.language_code) or languages.get("en") or {}
        return Translator(bundle, languages.get("en") or {})
