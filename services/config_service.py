from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from utils.config_loader import load_config


class ConfigService:
    REQUIRED_CONFIGS = (
        "system_config.json",
        "oauth_config.json",
        "feature_flags.json",
        "subscription_plans.json",
    )

    @lru_cache(maxsize=1)
    def load_all(self) -> dict[str, dict[str, Any]]:
        return {name: load_config(name) for name in self.REQUIRED_CONFIGS}

    def validate(self) -> list[str]:
        configs = self.load_all()
        issues: list[str] = []

        if "app" not in configs["system_config.json"]:
            issues.append("system_config.json is missing app settings.")
        if "google_oauth" not in configs["oauth_config.json"]:
            issues.append("oauth_config.json is missing google_oauth settings.")
        if "flags" not in configs["feature_flags.json"]:
            issues.append("feature_flags.json is missing flags.")
        if not configs["subscription_plans.json"].get("plans"):
            issues.append("subscription_plans.json must define at least one plan.")
        system_config = configs["system_config.json"]
        runtime_environment = system_config.get("app", {}).get("runtime_environment", "local")
        if runtime_environment not in {"local", "staging_cloud", "production"}:
            issues.append("system_config.json has invalid app.runtime_environment.")
        notification_mode = system_config.get("notifications", {}).get("notification_mode", "mock")
        if notification_mode not in {"mock", "live", "disabled"}:
            issues.append("system_config.json has invalid notifications.notification_mode.")
        return issues

    def clear_cache(self) -> None:
        self.load_all.cache_clear()

    def validate_streamlit_secrets(self, secrets: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        for section in ("security", "google", "admin"):
            if section not in secrets:
                issues.append(f"Missing Streamlit secrets section: {section}")
        required_fields = {
            "google": ("client_id", "client_secret", "redirect_uri"),
            "admin": ("admin_email",),
            "security": ("fernet_key", "public_verification_key"),
        }
        for section, fields in required_fields.items():
            values = secrets.get(section, {})
            for field in fields:
                if not str(values.get(field, "")).strip():
                    issues.append(f"Missing Streamlit secret: [{section}] {field}")
        return issues

    def validate_deployment_profile(self, system_config: dict[str, Any], oauth_config: dict[str, Any]) -> dict[str, list[str]]:
        blockers: list[str] = []
        warnings: list[str] = []
        runtime_environment = system_config.get("app", {}).get("runtime_environment", "local")
        redirect_uri = oauth_config.get("google_oauth", {}).get("redirect_uri", "")
        notification_mode = system_config.get("notifications", {}).get("notification_mode", "mock")
        demo_mode = bool(system_config.get("app", {}).get("demo_mode", False))
        enable_mock_auth = bool(system_config.get("security", {}).get("enable_mock_auth", False))

        if runtime_environment == "staging_cloud" and "localhost" in redirect_uri:
            blockers.append("staging_cloud runtime cannot use a localhost redirect URI.")
        if runtime_environment == "staging_cloud" and demo_mode:
            blockers.append("staging_cloud runtime cannot run with demo_mode=true.")
        if runtime_environment == "staging_cloud" and notification_mode != "live":
            blockers.append("staging_cloud runtime must use notification_mode=live.")
        if runtime_environment == "staging_cloud" and enable_mock_auth:
            blockers.append("staging_cloud runtime cannot expose mock authentication.")
        if runtime_environment == "production":
            if "localhost" in redirect_uri:
                blockers.append("production runtime cannot use a localhost redirect URI.")
            if demo_mode:
                blockers.append("production runtime cannot run with demo_mode=true.")
            if notification_mode != "live":
                blockers.append("production runtime must use notification_mode=live.")
            if enable_mock_auth:
                blockers.append("production runtime cannot expose mock authentication.")
        return {"blockers": blockers, "warnings": warnings}

    def write_latest_pilot_status(self, report_path: Path, payload: dict[str, Any]) -> None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
