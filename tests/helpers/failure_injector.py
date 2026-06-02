from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from services.safe_drive_write_service import SafeDriveWriteService


class LoggingStub:
    def __init__(self) -> None:
        self.errors: list[dict] = []
        self.infos: list[dict] = []

    def log_info(self, category, message, details=None):
        self.infos.append({"category": category, "message": message, "details": details or {}})

    def log_error(self, category, message, details=None):
        self.errors.append({"category": category, "message": message, "details": details or {}})


class AuditStub:
    def log_event(self, *_args, **_kwargs):
        return None

    def log_governance_event(self, *_args, **_kwargs):
        return None


@dataclass
class GmailStub:
    fail_on_types: set[str] = field(default_factory=set)
    sent: list[dict] = field(default_factory=list)

    def enqueue_message(self, to_email: str, subject: str, body: str, notification_type: str):
        if notification_type in self.fail_on_types:
            raise ValueError(f"forced gmail failure: {notification_type}")
        self.sent.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body": body,
                "notification_type": notification_type,
            }
        )


class FailingEventDispatcher:
    def __init__(self, delegate, fail_on_types: set[str] | None = None):
        self.delegate = delegate
        self.fail_on_types = fail_on_types or set()

    def emit(self, event_type, payload, producer="system"):
        if event_type in self.fail_on_types:
            raise ValueError(f"forced event failure: {event_type}")
        return self.delegate.emit(event_type, payload, producer=producer)


class FailingSafeWriteService(SafeDriveWriteService):
    def __init__(self, *args, fail_on_append: set[str] | None = None, fail_on_mutate_targets: set[str] | None = None, fail_on_replace_targets: set[str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fail_on_append = fail_on_append or set()
        self.fail_on_mutate_targets = fail_on_mutate_targets or set()
        self.fail_on_replace_targets = fail_on_replace_targets or set()

    def append_record(self, target, list_key, record, schema_name=None):
        if str(target) in self.fail_on_append:
            raise ValueError("forced append failure")
        return super().append_record(target, list_key, record, schema_name=schema_name)

    def mutate_json(self, target, mutator, schema_name=None, max_retries=3):
        if str(target) in self.fail_on_mutate_targets:
            raise ValueError("forced mutate failure")
        return super().mutate_json(target, mutator, schema_name=schema_name, max_retries=max_retries)

    def replace_document(self, target, payload, schema_name=None):
        if str(target) in self.fail_on_replace_targets:
            raise ValueError("forced replace failure")
        return super().replace_document(target, payload, schema_name=schema_name)


class UploadedFileStub:
    def __init__(self, name: str, content: bytes = b"proof"):
        self.name = name
        self._content = content

    def getbuffer(self):
        return self._content
