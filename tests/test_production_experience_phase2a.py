from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from components.command_palette import _build_quick_commands
from services.background_task_service import BackgroundTaskService
from services.bulk_action_service import BulkActionService
from services.json_service import JsonService
from services.recovery_action_service import RecoveryActionService


class _FakeSafeWriteService:
    def __init__(self) -> None:
        self.json_service = JsonService()

    def replace_document(self, target: Path, payload: dict, schema_name: str | None = None) -> dict:
        self.json_service.write_json(target, payload)
        return payload

    def append_record(self, target: Path, list_key: str, record: dict, schema_name: str | None = None) -> dict:
        payload = self.json_service.read_json(target, {"schema_version": "1.0", list_key: []})
        payload.setdefault(list_key, [])
        payload[list_key].append(record)
        self.json_service.write_json(target, payload)
        return payload

    def mutate_json(self, target: Path, mutator, schema_name: str | None = None) -> dict:
        payload = self.json_service.read_json(target, {"schema_version": "1.0"})
        updated = mutator(payload)
        self.json_service.write_json(target, updated)
        return updated


class _FakeIdAllocator:
    def __init__(self) -> None:
        self.counter = 0

    def allocate(self, domain: str) -> str:
        self.counter += 1
        return f"{domain.upper()}-{self.counter:03d}"


class _FakeNotificationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def update_status(self, manufacturer_code: str, notification_id: str, **kwargs):
        if notification_id == "NOTIF-FAIL":
            raise ValueError("boom")
        self.calls.append((manufacturer_code, notification_id))
        return {"notification_id": notification_id, **kwargs}

    def update_public_status(self, public_buyer_id: str, notification_id: str, **kwargs):
        self.calls.append((public_buyer_id, notification_id))
        return {"notification_id": notification_id, **kwargs}


class _FakeGmailService:
    def __init__(self) -> None:
        self.retried: list[str] = []
        self.queue = [{"email_id": "MAIL-1", "status": "FAILED"}, {"email_id": "MAIL-2", "status": "FAILED"}]

    def retry_failed(self, email_id: str):
        if email_id == "MAIL-FAIL":
            raise ValueError("cannot retry")
        self.retried.append(email_id)
        return {"email_id": email_id, "status": "RETRY"}

    def read_queue(self):
        return list(self.queue)

    def process_queue(self, max_messages: int = 10):
        return max_messages


def test_bulk_notification_actions_and_partial_failures():
    service = BulkActionService(
        notification_center_service=_FakeNotificationService(),
        public_buyer_service=SimpleNamespace(get_by_email=lambda _email: {"public_buyer_id": "PB-1"}),
        governance_service=SimpleNamespace(list_manufacturers=lambda: []),
        gmail_service=_FakeGmailService(),
        audit_service=None,
    )
    user = SimpleNamespace(role="manufacturer", manufacturer_code="MANU-1", email="ops@example.com")

    read_report = service.bulk_update_notifications(user=user, notification_ids=["NOTIF-1"], mark_read=True)
    resolve_report = service.bulk_update_notifications(user=user, notification_ids=["NOTIF-2"], resolved=True)
    partial_report = service.bulk_update_notifications(user=user, notification_ids=["NOTIF-3", "NOTIF-FAIL"], mark_read=True)
    retry_report = service.bulk_retry_failed_notifications(["MAIL-1", "MAIL-FAIL"])

    assert read_report["successes"] == ["NOTIF-1"]
    assert resolve_report["successes"] == ["NOTIF-2"]
    assert partial_report["successes"] == ["NOTIF-3"]
    assert partial_report["failures"][0]["notification_id"] == "NOTIF-FAIL"
    assert retry_report["successes"] == ["MAIL-1"]
    assert retry_report["failures"][0]["email_id"] == "MAIL-FAIL"


def test_background_task_service_tracks_lifecycle(tmp_path):
    service = BackgroundTaskService(
        runtime_root=tmp_path,
        safe_drive_write_service=_FakeSafeWriteService(),
        json_service=JsonService(),
        id_allocator_service=_FakeIdAllocator(),
        dead_letter_service=None,
    )

    task = service.run_task(task_type="EXPORT", message="Exporting rows", created_by="admin@example.com", runner=lambda: {"rows": 4})
    tasks = service.list_tasks()

    assert task["status"] == "SUCCESS"
    assert tasks[0]["task_type"] == "EXPORT"
    assert tasks[0]["created_by"] == "admin@example.com"


def test_recovery_actions_are_admin_only_and_create_task_records(tmp_path):
    background_task_service = BackgroundTaskService(
        runtime_root=tmp_path,
        safe_drive_write_service=_FakeSafeWriteService(),
        json_service=JsonService(),
        id_allocator_service=_FakeIdAllocator(),
        dead_letter_service=None,
    )
    service = RecoveryActionService(
        background_task_service=background_task_service,
        gmail_service=_FakeGmailService(),
        operational_search_service=SimpleNamespace(rebuild_index=lambda _ctx: {"indexed": 5}),
        kpi_service=SimpleNamespace(calculate_snapshot=lambda _ctx: {"health_scores": {"platform": 88}}),
        alert_engine=SimpleNamespace(generate_alerts=lambda _ctx: [{"alert_id": "A-1"}]),
        canonical_storage_validation_service=SimpleNamespace(validate=lambda: {"status": "PASS"}),
        settlement_service=SimpleNamespace(mark_overdue_transactions=lambda: [{"financial_transaction_id": "FTX-1"}]),
        automation_tasks=SimpleNamespace(run_hourly_tasks=lambda _ctx: {"task_window": "hourly"}),
        storage_cutover_service=SimpleNamespace(generate_cutover_readiness_report=lambda storage_mode_current="compatibility": {"recommendation": "READY", "storage_mode_current": storage_mode_current}),
    )

    try:
        service.execute("refresh_kpi_snapshot", {"system_config": {"storage": {"mode": "compatibility"}}}, actor_role="manufacturer", actor_id="user@example.com")
        raised = False
    except PermissionError:
        raised = True
    task = service.execute("refresh_kpi_snapshot", {"system_config": {"storage": {"mode": "compatibility"}}}, actor_role="platform_admin", actor_id="admin@example.com")

    assert raised is True
    assert task["status"] == "SUCCESS"
    assert background_task_service.list_tasks()[0]["task_type"] == "KPI_REFRESH"


def test_command_palette_quick_commands_include_recovery_actions():
    commands = _build_quick_commands(
        {
            "current_user": SimpleNamespace(role="platform_admin"),
            "recovery_action_service": SimpleNamespace(
                list_available_actions=lambda _role: [{"action_key": "refresh_kpi_snapshot", "label": "Refresh KPI Snapshot"}]
            ),
        },
        ["Products", "Jobs", "Raw Materials"],
        "refresh",
    )

    assert any(item.get("command_type") == "recovery_action" for item in commands)
