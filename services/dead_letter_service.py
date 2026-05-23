from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class DeadLetterService:
    def __init__(self, dead_letter_root: Path, id_allocator_service=None) -> None:
        self.dead_letter_root = dead_letter_root
        self.id_allocator_service = id_allocator_service

    def record(
        self,
        category: str,
        payload_snapshot: dict[str, Any],
        last_error: str,
        transaction_id: str = "",
        correlation_id: str = "",
        retry_history: list[dict[str, Any]] | None = None,
    ) -> Path:
        timestamp = datetime.now(UTC)
        month_dir = self.dead_letter_root / timestamp.strftime("%Y-%m")
        month_dir.mkdir(parents=True, exist_ok=True)
        entry_id = self.id_allocator_service.allocate("event") if self.id_allocator_service else f"DLQ-{timestamp.strftime('%Y%m%d%H%M%S%f')}"
        target = month_dir / f"{entry_id}.json"
        target.write_text(
            json.dumps(
                {
                    "entry_id": entry_id,
                    "category": category,
                    "timestamp": timestamp.isoformat(),
                    "transaction_id": transaction_id,
                    "correlation_id": correlation_id,
                    "payload_snapshot": payload_snapshot,
                    "retry_history": retry_history or [],
                    "last_error": last_error,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return target

    def list_entries(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.dead_letter_root.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.dead_letter_root.glob("*/*.json"), reverse=True)[:limit]:
            try:
                rows.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return rows
