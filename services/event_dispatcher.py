from __future__ import annotations
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class EventDispatcher:
    def __init__(self, events_root: Path, id_allocator_service, dead_letter_service=None, logging_service=None, runtime_metrics_service=None) -> None:
        self.events_root = events_root
        self.id_allocator_service = id_allocator_service
        self.dead_letter_service = dead_letter_service
        self.logging_service = logging_service
        self.runtime_metrics_service = runtime_metrics_service
        self.handlers = {}

    def _index_path(self, timestamp: datetime) -> Path:
        return self.events_root / "index" / f"{timestamp.strftime('%Y-%m')}.jsonl"

    def on(self, event_type: str, handler: Any) -> None:
        self.handlers.setdefault(event_type, []).append(handler)

    def emit(self, event_type: str, payload: dict[str, Any], producer: str = "system") -> dict[str, Any]:
        event_id = self.id_allocator_service.allocate("event")
        timestamp = datetime.now(UTC)
        event_record = {
            "event_id": event_id,
            "event_type": event_type,
            "event_version": "1.0",
            "transaction_id": payload.get("transaction_id", ""),
            "correlation_id": payload.get("correlation_id", payload.get("order_id", payload.get("agreement_id", payload.get("request_id", "")))),
            "timestamp": timestamp.isoformat(),
            "producer": producer,
            "payload": payload,
        }
        month_dir = self.events_root / timestamp.strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)
        try:
            target = month_dir / f"{event_id}.json"
            target.write_text(json.dumps(event_record, indent=2), encoding="utf-8")
            index_path = self._index_path(timestamp)
            index_path.parent.mkdir(parents=True, exist_ok=True)
            with index_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"event_id": event_id, "event_type": event_type, "transaction_id": event_record["transaction_id"], "correlation_id": event_record["correlation_id"], "producer": producer, "path": str(target)}, ensure_ascii=True) + "\n")
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("events_emitted", extra={"event_type": event_type})
        except Exception as exc:  # noqa: BLE001
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("event_failures", extra={"event_type": event_type})
            if self.logging_service:
                self.logging_service.log_error("event_failures", "Event persistence failed", {"event_type": event_type, "error": str(exc)})
            if self.dead_letter_service:
                self.dead_letter_service.record(
                    "event_persistence_failure",
                    event_record,
                    str(exc),
                    transaction_id=event_record["transaction_id"],
                    correlation_id=event_record["correlation_id"],
                )
            raise

        for handler in self.handlers.get(event_type, []):
            handler(event_record)
        return event_record
