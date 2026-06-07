from __future__ import annotations

import streamlit as st


class Translator:
    def __init__(self, bundle: dict[str, str], *, language_code: str, fallback_bundle: dict[str, str] | None = None) -> None:
        self.bundle = bundle
        self.language_code = language_code
        self.fallback_bundle = fallback_bundle or {}

    def t(self, key: str) -> str:
        normalized_key = str(key or "").strip()
        value = self.bundle.get(normalized_key)
        if value is None:
            fallback_value = self.fallback_bundle.get(normalized_key)
            if fallback_value is not None:
                return str(fallback_value)
            missing = dict(st.session_state.get("mt_missing_translation_keys", {}) or {})
            language_missing = set(missing.get(self.language_code, []) or [])
            language_missing.add(normalized_key)
            missing[self.language_code] = sorted(language_missing)
            st.session_state["mt_missing_translation_keys"] = missing
            return normalized_key
        return str(value)


class LanguageService:
    SESSION_KEY = "mt_language"

    def __init__(self, cache_service, language_code: str | None = None) -> None:
        self.cache_service = cache_service
        self.language_code = language_code or self.get_current_language()
        st.session_state.setdefault("mt_missing_translation_keys", {})

    def get_language_bundles(self) -> dict[str, dict[str, str]]:
        return dict(self.cache_service.get_config("languages") or {})

    def get_available_languages(self) -> list[str]:
        return sorted(self.get_language_bundles().keys())

    def get_current_language(self) -> str:
        bundles = self.get_language_bundles()
        default_language = "en"
        selected = str(st.session_state.get(self.SESSION_KEY, default_language) or default_language)
        if selected in bundles:
            return selected
        return default_language if default_language in bundles else (next(iter(bundles.keys()), default_language))

    def set_current_language(self, lang_code: str) -> None:
        st.session_state[self.SESSION_KEY] = str(lang_code or "en")
        st.session_state["mt_next_language"] = st.session_state[self.SESSION_KEY]
        self.language_code = st.session_state[self.SESSION_KEY]

    def get_translator(self) -> Translator:
        bundles = self.get_language_bundles()
        code = self.language_code if self.language_code in bundles else self.get_current_language()
        fallback_bundle = dict(bundles.get("en", {}) or {})
        return Translator(dict(bundles.get(code, {}) or {}), language_code=code, fallback_bundle=fallback_bundle)

    def t(self, key: str) -> str:
        return self.get_translator().t(key)

    def get_key_count_map(self) -> dict[str, int]:
        return {
            code: len(bundle or {})
            for code, bundle in self.get_language_bundles().items()
        }

    def get_missing_keys_for_current_language(self) -> list[str]:
        code = self.get_current_language()
        missing = dict(st.session_state.get("mt_missing_translation_keys", {}) or {})
        return list(missing.get(code, []) or [])
