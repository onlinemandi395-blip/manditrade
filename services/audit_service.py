from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
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

    def read_structured_events(
        self,
        *,
        actor: str = "",
        entity_type: str = "",
        severity: str = "",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if not self.audit_dir.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.audit_dir.glob("*.jsonl"), reverse=True):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if actor and str(row.get("actor", "")).strip().lower() != actor.strip().lower():
                    continue
                if entity_type and str(row.get("entity_type", "")).strip().lower() != entity_type.strip().lower():
                    continue
                if severity and str(row.get("details", {}).get("severity", "")).strip().upper() != severity.strip().upper():
                    continue
                rows.append(row)
                if len(rows) >= limit:
                    return rows
        return rows

    def summarize_structured_events(self) -> dict[str, Any]:
        rows = self.read_structured_events(limit=500)
        return {
            "total_events": len(rows),
            "warning_events": len([row for row in rows if str(row.get("details", {}).get("severity", "")).upper() in {"HIGH", "CRITICAL"}]),
            "actors": len({str(row.get("actor", "")) for row in rows if row.get("actor")}),
            "entities": len({f"{row.get('entity_type', '')}:{row.get('entity_id', '')}" for row in rows if row.get("entity_id")}),
        }

    def archive_old_logs(self, *, keep_days: int = 30) -> int:
        if not self.audit_dir.exists():
            return 0
        archive_dir = self.audit_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.now(UTC).date() - timedelta(days=keep_days)
        moved = 0
        for path in self.audit_dir.glob("*.jsonl"):
            try:
                file_date = datetime.fromisoformat(path.stem).date()
            except ValueError:
                continue
            if file_date < cutoff:
                target = archive_dir / path.name
                path.replace(target)
                moved += 1
        return moved
