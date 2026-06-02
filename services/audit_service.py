from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditService:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.audit_dir = log_path.parent / "audit_logs"

    def log_event(self, event_type: str, actor: str, details: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "actor": actor,
            "details": details,
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry, ensure_ascii=True) + "\n")
        self._write_structured_entry(
            {
                "timestamp": entry["timestamp"],
                "role": str(details.get("role", "") or ""),
                "action": event_type,
                "actor": actor,
                "entity_type": str(details.get("entity_type", "") or ""),
                "entity_id": str(details.get("entity_id", "") or ""),
                "details": details,
            }
        )

    def log_governance_event(
        self,
        *,
        actor: str,
        role: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "role": role,
            "action": action,
            "actor": actor,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
        self._write_structured_entry(payload)

    def _write_structured_entry(self, payload: dict[str, Any]) -> None:
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        date_key = str(payload.get("timestamp", datetime.now(UTC).isoformat()))[:10]
        target = self.audit_dir / f"{date_key}.jsonl"
        with target.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def read_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        recent = lines[-limit:]
        return [json.loads(line) for line in recent if line.strip()]
