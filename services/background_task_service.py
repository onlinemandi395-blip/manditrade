from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


class BackgroundTaskService:
    def __init__(
        self,
        *,
        runtime_root: Path,
        safe_drive_write_service,
        json_service,
        id_allocator_service,
        dead_letter_service=None,
    ) -> None:
        self.runtime_root = runtime_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.dead_letter_service = dead_letter_service

    @property
    def tasks_path(self) -> Path:
        return self.runtime_root / "background_tasks" / "tasks.json"

    def ensure_store(self) -> None:
        if not self.tasks_path.exists():
            self.safe_drive_write_service.replace_document(
                self.tasks_path,
                {"schema_version": "1.0", "tasks": []},
            )

    def list_tasks(self, *, limit: int = 50, statuses: set[str] | None = None) -> list[dict[str, Any]]:
        self.ensure_store()
        tasks = self.json_service.read_json(self.tasks_path, {"tasks": []}).get("tasks", [])
        filtered = [
            item
            for item in tasks
            if not statuses or str(item.get("status", "")).upper() in statuses
        ]
        filtered.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return filtered[:limit]

    def create_task(self, *, task_type: str, message: str = "", created_by: str = "system") -> dict[str, Any]:
        self.ensure_store()
        now = datetime.now(UTC).isoformat()
        task = {
            "task_id": self.id_allocator_service.allocate("task"),
            "task_type": str(task_type or "").strip().upper(),
            "status": "QUEUED",
            "progress": 0,
            "message": str(message or "").strip(),
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "result_ref": "",
            "error": "",
        }
        self.safe_drive_write_service.append_record(self.tasks_path, "tasks", task)
        return task

    def update_task(self, task_id: str, **updates: Any) -> dict[str, Any]:
        self.ensure_store()
        updated: dict[str, Any] | None = None

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal updated
            for item in payload.get("tasks", []):
                if item.get("task_id") == task_id:
                    item.update(updates)
                    item["updated_at"] = datetime.now(UTC).isoformat()
                    updated = dict(item)
                    return payload
            raise ValueError(f"Background task not found: {task_id}")

        self.safe_drive_write_service.mutate_json(self.tasks_path, mutator)
        return updated or {}

    def run_task(
        self,
        *,
        task_type: str,
        runner: Callable[[], Any],
        message: str = "",
        created_by: str = "system",
    ) -> dict[str, Any]:
        task = self.create_task(task_type=task_type, message=message, created_by=created_by)
        self.update_task(task["task_id"], status="RUNNING", progress=15, message=message or task_type.replace("_", " ").title())
        try:
            result = runner()
            result_ref = ""
            if isinstance(result, dict) and result.get("report_path"):
                result_ref = str(result.get("report_path", ""))
            updated = self.update_task(
                task["task_id"],
                status="SUCCESS",
                progress=100,
                result_ref=result_ref,
                error="",
                message=str(message or "Completed successfully."),
            )
            updated["result"] = result
            return updated
        except Exception as exc:  # noqa: BLE001
            if self.dead_letter_service:
                self.dead_letter_service.record(
                    "background_task_failed",
                    {"task_id": task["task_id"], "task_type": task_type, "message": message},
                    str(exc),
                    correlation_id=task["task_id"],
                )
            updated = self.update_task(
                task["task_id"],
                status="FAILED",
                progress=100,
                error=str(exc),
                message=str(message or "Task failed."),
            )
            updated["result"] = None
            return updated
