from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from utils.file_locking import atomic_write_text


class AutomationTasks:
    def __init__(self, *, runtime_root: Path, alert_engine, recommendation_service, kpi_service, audit_service, safe_drive_write_service=None, event_bus=None) -> None:
        self.runtime_root = runtime_root
        self.alert_engine = alert_engine
        self.recommendation_service = recommendation_service
        self.kpi_service = kpi_service
        self.audit_service = audit_service
        self.safe_drive_write_service = safe_drive_write_service
        self.event_bus = event_bus

    def run_hourly_tasks(self, app_context: dict) -> dict[str, Any]:
        alerts = self.alert_engine.generate_alerts(app_context)
        kpis = self.kpi_service.calculate_snapshot(app_context)
        recommendations = self.recommendation_service.generate(app_context)
        self._write_snapshot("hourly", {"kpis": kpis, "alerts": self.alert_engine.read_snapshot(), "recommendations": recommendations})
        result = {
            "ran_at": datetime.now(UTC).isoformat(),
            "task_window": "hourly",
            "alerts_generated": len(alerts),
            "recommendation_groups": len(recommendations),
            "platform_health": kpis.get("health_scores", {}).get("platform", 0),
        }
        self._write_result("hourly", result)
        self._publish("HOURLY_TASKS_COMPLETED", result)
        return result

    def run_daily_tasks(self, app_context: dict) -> dict[str, Any]:
        alerts = self.alert_engine.generate_alerts(app_context)
        kpis = self.kpi_service.calculate_snapshot(app_context)
        recommendations = self.recommendation_service.generate(app_context)
        archived_logs = self.audit_service.archive_old_logs(keep_days=30)
        self._write_snapshot("daily", {"kpis": kpis, "alerts": self.alert_engine.read_snapshot(), "recommendations": recommendations})
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
        self._publish("DAILY_TASKS_COMPLETED", result)
        return result

    def _write_result(self, task_name: str, payload: dict[str, Any]) -> None:
        target = self.runtime_root / "automation" / f"{task_name}.json"
        self._write_payload(target, payload)

    def _write_snapshot(self, snapshot_name: str, payload: dict[str, Any]) -> None:
        target = self.runtime_root / "analytics_snapshots" / f"{snapshot_name}.json"
        self._write_payload(target, payload)

    def _write_payload(self, target: Path, payload: dict[str, Any]) -> None:
        if self.safe_drive_write_service:
            self.safe_drive_write_service.replace_document(target, payload)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target, json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            self.event_bus.publish(event_type, payload)
