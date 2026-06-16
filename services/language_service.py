from __future__ import annotations

import re

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
            return self._humanize_key(normalized_key)
        return str(value)

    @staticmethod
    def _humanize_key(key: str) -> str:
        normalized = str(key or "").strip()
        if not normalized:
            return ""
        parts = [part for part in normalized.split(".") if part]
        candidate = parts[-1] if parts else normalized
        if len(parts) >= 2 and candidate.lower() in {"title", "subtitle", "desc", "label", "name"}:
            candidate = parts[-2]
        candidate = candidate.replace("-", " ").replace("_", " ")
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if not candidate:
            return normalized
        words = []
        for word in candidate.split(" "):
            upper_word = word.upper()
            if upper_word in {"UPI", "OTP", "JSON", "RBAC", "UI"}:
                words.append(upper_word)
            elif word.lower() == "oauth":
                words.append("OAuth")
            else:
                words.append(word.capitalize())
        return " ".join(words)


class LanguageService:
    SESSION_KEY = "mt_language"

    def __init__(self, cache_service, language_code: str | None = None) -> None:
        self.cache_service = cache_service
        self.language_code = language_code or self.get_current_language()
        st.session_state.setdefault("mt_missing_translation_keys", {})

    def _get_language_codes(self) -> list[str]:
        preferred_codes = list(self.cache_service.config_loader_service.list_available_language_codes())
        if "en" not in preferred_codes:
            preferred_codes.append("en")
        return sorted({str(code or "").strip().lower() for code in preferred_codes if str(code or "").strip()})

    def _get_language_bundle(self, code: str) -> dict[str, str]:
        normalized_code = str(code or "").strip().lower()
        if not normalized_code:
            return {}
        cache_key = f"language::{normalized_code}"
        cached = self.cache_service.get_config(cache_key)
        if cached:
            return dict(cached or {})
        bundle = dict(self.cache_service.config_loader_service.load_language(normalized_code) or {})
        self.cache_service.update_config(cache_key, bundle)
        return bundle

    def get_language_bundles(self) -> dict[str, dict[str, str]]:
        return {
            code: self._get_language_bundle(code)
            for code in self._get_language_codes()
        }

    def get_available_languages(self) -> list[str]:
        bundles = self.get_language_bundles()
        app_config = dict(self.cache_service.get_config("app_config") or {})
        preferred_order = list((((app_config.get("ui") or {}).get("languages") or {}).get("preferred_order", [])) or [])
        ordered = []
        seen = set()
        for code in preferred_order:
            normalized = str(code or "").strip().lower()
            if normalized and normalized in bundles and normalized not in seen:
                ordered.append(normalized)
                seen.add(normalized)
        for code in sorted(bundles.keys()):
            if code not in seen:
                ordered.append(code)
        return ordered

    def get_language_option_labels(self) -> dict[str, str]:
        bundles = self.get_language_bundles()
        labels: dict[str, str] = {}
        for code, bundle in bundles.items():
            native = str(bundle.get("meta.language_native_name", "") or "").strip()
            english = str(bundle.get("meta.language_name", "") or "").strip()
            if native and english and native != english:
                labels[code] = f"{native} ({english})"
            elif native or english:
                labels[code] = native or english
            else:
                labels[code] = str(code or "").upper()
        return labels

    def get_current_language(self) -> str:
        bundles = self._get_language_codes()
        default_language = "en"
        selected = str(st.session_state.get(self.SESSION_KEY, default_language) or default_language)
        if selected in bundles:
            return selected
        return default_language if default_language in bundles else (bundles[0] if bundles else default_language)

    def set_current_language(self, lang_code: str) -> None:
        st.session_state[self.SESSION_KEY] = str(lang_code or "en")
        st.session_state["mt_next_language"] = st.session_state[self.SESSION_KEY]
        self.language_code = st.session_state[self.SESSION_KEY]

    def get_translator(self) -> Translator:
        available_codes = self._get_language_codes()
        code = self.language_code if self.language_code in available_codes else self.get_current_language()
        fallback_bundle = self._get_language_bundle("en")
        return Translator(self._get_language_bundle(code), language_code=code, fallback_bundle=fallback_bundle)

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
