from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AutomationTasks:
    def __init__(self, *, runtime_root: Path, alert_engine, recommendation_service, kpi_service, audit_service) -> None:
        self.runtime_root = runtime_root
        self.alert_engine = alert_engine
        self.recommendation_service = recommendation_service
        self.kpi_service = kpi_service
        self.audit_service = audit_service

    def run_hourly_tasks(self, app_context: dict) -> dict[str, Any]:
        alerts = self.alert_engine.generate_alerts(app_context)
        kpis = self.kpi_service.calculate_snapshot(app_context)
        recommendations = self.recommendation_service.generate(app_context)
        result = {
            "ran_at": datetime.now(UTC).isoformat(),
            "task_window": "hourly",
            "alerts_generated": len(alerts),
            "recommendation_groups": len(recommendations),
            "platform_health": kpis.get("health_scores", {}).get("platform", 0),
        }
        self._write_result("hourly", result)
        return result

    def run_daily_tasks(self, app_context: dict) -> dict[str, Any]:
        alerts = self.alert_engine.generate_alerts(app_context)
        kpis = self.kpi_service.calculate_snapshot(app_context)
        recommendations = self.recommendation_service.generate(app_context)
        archived_logs = self.audit_service.archive_old_logs(keep_days=30)
        result = {
            "ran_at": datetime.now(UTC).isoformat(),
            "task_window": "daily",
            "alerts_generated": len(alerts),
            "recommendation_groups": len(recommendations),
            "platform_health": kpis.get("health_scores", {}).get("platform", 0),
            "archived_logs": archived_logs,
            "orphan_records_cleaned": 0,
        }
        self._write_result("daily", result)
        return result

    def _write_result(self, task_name: str, payload: dict[str, Any]) -> None:
        target = self.runtime_root / "automation" / f"{task_name}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
