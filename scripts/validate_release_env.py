from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.config_service import ConfigService
from utils.config_loader import load_config
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, STREAMLIT_DIR

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


def _load_secrets() -> dict[str, Any]:
    secrets_path = STREAMLIT_DIR / "secrets.toml"
    if not secrets_path.exists() or tomllib is None:
        return {}
    return tomllib.loads(secrets_path.read_text(encoding="utf-8"))


def _build_report() -> dict[str, Any]:
    config_service = ConfigService()
    system_config = load_config("system_config.json")
    oauth_config = load_config("oauth_config.json")
    secrets = _load_secrets()

    config_issues = config_service.validate()
    secret_issues = config_service.validate_streamlit_secrets(secrets)
    deployment = config_service.validate_deployment_profile(
        system_config,
        oauth_config,
        oauth_secrets_override_active=bool(secrets.get("google", {}).get("client_id")),
        oauth_config_fallback_active=not bool(secrets.get("google", {}).get("client_id")),
    )

    blockers = list(config_issues) + list(secret_issues) + list(deployment["blockers"])
    warnings = list(deployment["warnings"])
    checks: list[dict[str, Any]] = []

    runtime_environment = str(system_config.get("app", {}).get("runtime_environment", "local"))
    notification_mode = str(system_config.get("notifications", {}).get("notification_mode", "mock"))
    redirect_uri = str(oauth_config.get("google_oauth", {}).get("redirect_uri", ""))
    safe_mode = bool(system_config.get("app", {}).get("safe_mode", False))
    demo_mode = bool(system_config.get("app", {}).get("demo_mode", False))
    mock_auth = bool(system_config.get("security", {}).get("enable_mock_auth", False))
    admin_sender_email = str(system_config.get("notifications", {}).get("admin_sender_email", "")).strip()

    def add_check(name: str, passed: bool, detail: str, *, severity: str = "BLOCKER") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail, "severity": severity})
        if passed:
            return
        if severity == "WARNING":
            warnings.append(detail)
        else:
            blockers.append(detail)

    add_check(
        "runtime_environment_valid",
        runtime_environment in {"local", "staging_cloud", "production"},
        f"Invalid runtime_environment: {runtime_environment}",
    )
    add_check(
        "notification_mode_valid",
        notification_mode in {"mock", "live", "disabled"},
        f"Invalid notification_mode: {notification_mode}",
    )
    add_check(
        "safe_mode_enabled",
        safe_mode or runtime_environment == "local",
        "safe_mode should stay enabled for staging_cloud or production release validation.",
    )
    add_check(
        "admin_sender_email_configured",
        bool(admin_sender_email) and not admin_sender_email.endswith(".local"),
        "Admin sender email is missing or still uses a .local placeholder.",
    )
    add_check(
        "google_client_id_present",
        bool(str(secrets.get("google", {}).get("client_id", "")).strip()),
        "Google OAuth client_id is missing from Streamlit secrets.",
    )
    add_check(
        "google_client_secret_present",
        bool(str(secrets.get("google", {}).get("client_secret", "")).strip()),
        "Google OAuth client_secret is missing from Streamlit secrets.",
    )
    add_check(
        "google_redirect_uri_present",
        bool(str(secrets.get("google", {}).get("redirect_uri", "")).strip() or redirect_uri.strip()),
        "Google OAuth redirect URI is missing.",
    )
    add_check(
        "cloud_redirect_is_not_localhost",
        runtime_environment == "local" or "localhost" not in redirect_uri.lower(),
        "Cloud runtime cannot use a localhost OAuth redirect URI.",
    )
    add_check(
        "mock_auth_disabled_for_release",
        runtime_environment == "local" or not mock_auth,
        "Mock authentication must stay disabled outside local runtime.",
    )
    add_check(
        "demo_mode_disabled_for_release",
        runtime_environment == "local" or not demo_mode,
        "demo_mode must stay disabled for pilot release packaging.",
    )
    add_check(
        "public_verification_key_present",
        bool(str(secrets.get("security", {}).get("public_verification_key", "")).strip()),
        "Public verification key is missing from Streamlit secrets.",
    )
    add_check(
        "admin_email_secret_present",
        bool(str(secrets.get("admin", {}).get("admin_email", "")).strip()),
        "Admin email is missing from Streamlit secrets.",
    )

    dedup_blockers = list(dict.fromkeys(blockers))
    dedup_warnings = list(dict.fromkeys(warnings))
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "repo_root": str(BASE_DIR),
        "runtime_environment": runtime_environment,
        "notification_mode": notification_mode,
        "safe_mode": safe_mode,
        "status": "PASS" if not dedup_blockers else "FAIL",
        "blockers": dedup_blockers,
        "warnings": dedup_warnings,
        "checks": checks,
        "streamlit_secrets_present": bool(secrets),
    }


def _write_report(report: dict[str, Any]) -> Path:
    report_dir = APP_RUNTIME_DIR / "release_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = report_dir / f"release_env_{timestamp}.json"
    latest = report_dir / "latest_release_env.json"
    payload = json.dumps(report, indent=2, ensure_ascii=True)
    target.write_text(payload, encoding="utf-8")
    latest.write_text(payload, encoding="utf-8")
    return target


def main() -> int:
    report = _build_report()
    target = _write_report(report)
    print(f"Release environment validation: {report['status']}")
    print(f"Runtime environment: {report['runtime_environment']}")
    print(f"Notification mode: {report['notification_mode']}")
    if report["blockers"]:
        print("Blockers:")
        for issue in report["blockers"]:
            print(f"- {issue}")
    if report["warnings"]:
        print("Warnings:")
        for issue in report["warnings"]:
            print(f"- {issue}")
    print(f"JSON report: {target}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
