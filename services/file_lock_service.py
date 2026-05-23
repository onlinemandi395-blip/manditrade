from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

from utils.paths import APP_RUNTIME_DIR


class FileLockService:
    def __init__(self) -> None:
        self.locks_dir = APP_RUNTIME_DIR / "locks"

    def _lock_path(self, target: Path) -> Path:
        safe_name = target.as_posix().replace("/", "__").replace(":", "")
        return self.locks_dir / f"{safe_name}.lock.json"

    def acquire(
        self,
        target: Path,
        timeout_seconds: float = 5.0,
        poll_interval: float = 0.1,
        owner: str = "system",
        session_id: str | None = None,
        stale_after_seconds: float = 30.0,
    ) -> Path:
        lock_path = self._lock_path(target)
        deadline = time.time() + timeout_seconds
        while lock_path.exists():
            try:
                payload = json.loads(lock_path.read_text(encoding="utf-8"))
                if (time.time() - float(payload.get("created_at_epoch", 0))) > stale_after_seconds:
                    lock_path.unlink(missing_ok=True)
                    break
            except Exception:
                lock_path.unlink(missing_ok=True)
                break
            if time.time() >= deadline:
                raise TimeoutError(f"Timed out waiting for lock on {target}")
            time.sleep(poll_interval)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(
            json.dumps(
                {
                    "target": str(target),
                    "owner": owner,
                    "session_id": session_id or uuid4().hex,
                    "created_at_epoch": time.time(),
                }
            ),
            encoding="utf-8",
        )
        return lock_path

    def release(self, lock_path: Path) -> None:
        if lock_path.exists():
            lock_path.unlink()

    def cleanup_stale_locks(self, stale_after_seconds: float = 30.0) -> list[dict]:
        cleaned: list[dict] = []
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        for lock_path in self.locks_dir.glob("*.lock.json"):
            try:
                payload = json.loads(lock_path.read_text(encoding="utf-8"))
                if (time.time() - float(payload.get("created_at_epoch", 0))) > stale_after_seconds:
                    cleaned.append(payload)
                    lock_path.unlink(missing_ok=True)
            except Exception:
                cleaned.append({"target": str(lock_path), "owner": "unknown"})
                lock_path.unlink(missing_ok=True)
        return cleaned
