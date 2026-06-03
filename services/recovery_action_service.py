from __future__ import annotations

from typing import Any


class RecoveryActionService:
    ACTIONS = {
        "retry_failed_gmail_queue": {
            "label": "Retry Failed Email Queue",
            "task_type": "NOTIFICATION_QUEUE_RETRY",
            "message": "Retrying failed Gmail queue items.",
        },
        "rebuild_search_index": {
            "label": "Rebuild Search Index",
            "task_type": "SEARCH_INDEX_REBUILD",
            "message": "Rebuilding the operational search index.",
        },
        "refresh_kpi_snapshot": {
            "label": "Refresh KPI Snapshot",
            "task_type": "KPI_REFRESH",
            "message": "Refreshing KPI snapshot.",
        },
        "regenerate_alerts": {
            "label": "Regenerate Alerts",
            "task_type": "ALERT_REFRESH",
            "message": "Regenerating operational alerts.",
        },
        "rerun_canonical_validation": {
            "label": "Rerun Canonical Validation",
            "task_type": "CANONICAL_STORAGE_VALIDATION",
            "message": "Running canonical storage validation.",
        },
        "refresh_overdue_detection": {
            "label": "Refresh Overdue Detection",
            "task_type": "OVERDUE_REFRESH",
            "message": "Refreshing overdue settlement detection.",
        },
        "run_hourly_automation": {
            "label": "Run Hourly Automation",
            "task_type": "HOURLY_AUTOMATION",
            "message": "Running hourly automation tasks.",
        },
        "generate_cutover_readiness_report": {
            "label": "Generate Cutover Readiness Report",
            "task_type": "CUTOVER_READINESS_REPORT",
            "message": "Generating storage cutover readiness report.",
        },
    }

    def __init__(
        self,
        *,
        background_task_service,
        gmail_service,
        operational_search_service,
        kpi_service,
        alert_engine,
        canonical_storage_validation_service,
        settlement_service,
        automation_tasks,
        storage_cutover_service,
    ) -> None:
        self.background_task_service = background_task_service
        self.gmail_service = gmail_service
        self.operational_search_service = operational_search_service
        self.kpi_service = kpi_service
        self.alert_engine = alert_engine
        self.canonical_storage_validation_service = canonical_storage_validation_service
        self.settlement_service = settlement_service
        self.automation_tasks = automation_tasks
        self.storage_cutover_service = storage_cutover_service

    def list_available_actions(self, role: str) -> list[dict[str, str]]:
        if str(role or "").strip().lower() != "platform_admin":
            return []
        return [
            {"action_key": key, "label": value["label"]}
            for key, value in self.ACTIONS.items()
        ]

    def execute(self, action_key: str, app_context: dict, *, actor_role: str, actor_id: str = "platform_admin") -> dict[str, Any]:
        if str(actor_role or "").strip().lower() != "platform_admin":
            raise PermissionError("Recovery actions are admin-only.")
        if action_key not in self.ACTIONS:
            raise ValueError(f"Unsupported recovery action: {action_key}")
        action = self.ACTIONS[action_key]
        return self.background_task_service.run_task(
            task_type=action["task_type"],
            message=action["message"],
            created_by=actor_id,
            runner=lambda: self._run_action(action_key, app_context),
        )

    def _run_action(self, action_key: str, app_context: dict) -> dict[str, Any]:
        if action_key == "retry_failed_gmail_queue":
            queue = self.gmail_service.read_queue()
            failed = [item for item in queue if str(item.get("status", "")).upper() == "FAILED"]
            for item in failed:
                self.gmail_service.retry_failed(item.get("email_id", ""))
            processed = self.gmail_service.process_queue(max_messages=len(failed)) if failed else 0
            return {"retried": len(failed), "processed": processed}
        if action_key == "rebuild_search_index":
            return self.operational_search_service.rebuild_index(app_context)
        if action_key == "refresh_kpi_snapshot":
            return self.kpi_service.calculate_snapshot(app_context)
        if action_key == "regenerate_alerts":
            return {"alerts": self.alert_engine.generate_alerts(app_context)}
        if action_key == "rerun_canonical_validation":
            return self.canonical_storage_validation_service.validate()
        if action_key == "refresh_overdue_detection":
            updated = self.settlement_service.mark_overdue_transactions()
            return {"updated_transactions": len(updated), "transactions": updated}
        if action_key == "run_hourly_automation":
            return self.automation_tasks.run_hourly_tasks(app_context)
        if action_key == "generate_cutover_readiness_report":
            return self.storage_cutover_service.generate_cutover_readiness_report(
                storage_mode_current=app_context["system_config"]["storage"].get("mode", "compatibility")
            )
        raise ValueError(f"Unsupported recovery action: {action_key}")
