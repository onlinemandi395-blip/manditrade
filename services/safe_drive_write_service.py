from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from services.file_lock_service import FileLockService
from services.logging_service import LoggingService
from services.schema_validation_service import SchemaValidationService
from services.cache_service import CacheService


class SafeDriveWriteService:
    def __init__(
        self,
        json_service,
        file_lock_service: FileLockService,
        schema_validation_service: SchemaValidationService,
        backups_root: Path,
        logging_service: LoggingService,
        version_history_root: Path,
    ) -> None:
        self.json_service = json_service
        self.file_lock_service = file_lock_service
        self.schema_validation_service = schema_validation_service
        self.backups_root = backups_root
        self.logging_service = logging_service
        self.version_history_root = version_history_root
        self.cache_service = CacheService(ttl_seconds=15)

    def _document_hash(self, payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _version_history_path(self, target: Path) -> Path:
        safe_name = target.as_posix().replace("/", "__").replace(":", "")
        return self.version_history_root / f"{safe_name}.history.json"

    def _record_version_history(self, target: Path, payload: dict[str, Any]) -> None:
        history_path = self._version_history_path(target)
        history = self.json_service.read_json(history_path, {"versions": []})
        history["versions"].append(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "target": str(target),
                "document_hash": payload.get("document_hash", ""),
                "version": payload.get("_version", ""),
            }
        )
        history_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_service.write_json(history_path, history)

    def _backup_path(self, target: Path) -> Path:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        safe_name = target.as_posix().replace("/", "__").replace(":", "")
        return self.backups_root / f"{safe_name}.{timestamp}.bak"

    def backup_file(self, target: Path) -> Path | None:
        if not target.exists():
            return None
        backup = self._backup_path(target)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        return backup

    def restore_latest_backup(self, target: Path) -> bool:
        safe_name = target.as_posix().replace("/", "__").replace(":", "")
        backups = sorted(self.backups_root.glob(f"{safe_name}.*.bak"))
        if not backups:
            return False
        shutil.copy2(backups[-1], target)
        return True

    def safe_write_json(
        self,
        target: Path,
        payload: dict[str, Any],
        schema_name: str | None = None,
        expected_version: str | None = None,
        owner: str = "system",
        session_id: str | None = None,
    ) -> None:
        lock_path = self.file_lock_service.acquire(target, owner=owner, session_id=session_id)
        try:
            latest = self.json_service.read_json(target, {}) if target.exists() else {}
            latest_version = str(latest.get("_version", "")) if isinstance(latest, dict) else ""
            if expected_version is not None and latest_version and latest_version != expected_version:
                raise ValueError(f"Stale write blocked for {target}")
            if schema_name:
                payload.setdefault("schema_version", self.schema_validation_service.get_schema_version(schema_name))
                self.schema_validation_service.validate(schema_name, payload)
            backup = self.backup_file(target)
            payload["_version"] = datetime.now(UTC).isoformat()
            payload["document_hash"] = self._document_hash(payload)
            self.json_service.write_json(target, payload)
            self.cache_service.invalidate("json", str(target))
            try:
                verified = json.loads(target.read_text(encoding="utf-8"))
                if verified.get("document_hash") != payload["document_hash"]:
                    raise ValueError("Post-write checksum mismatch")
                self._record_version_history(target, verified)
            except Exception as exc:  # noqa: BLE001
                if backup:
                    shutil.copy2(backup, target)
                raise ValueError(f"Verification failed after write: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            self.logging_service.log_error("drive_failures", str(exc), {"target": str(target)})
            raise
        finally:
            self.file_lock_service.release(lock_path)

    def mutate_json(
        self,
        target: Path,
        mutator: Callable[[dict[str, Any]], dict[str, Any]],
        schema_name: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        for attempt in range(max_retries):
            try:
                current = self.json_service.read_json(target, {}) if target.exists() else {}
                updated = mutator(current)
                expected_version = str(current.get("_version", "")) if isinstance(current, dict) else None
                self.safe_write_json(target, updated, schema_name=schema_name, expected_version=expected_version)
                return updated
            except Exception as exc:  # noqa: BLE001
                if attempt == max_retries - 1:
                    raise
                self.logging_service.log_error(
                    "drive_failures",
                    "Retrying safe write",
                    {"target": str(target), "attempt": attempt + 1, "error": str(exc)},
                )
                time.sleep(0.2 * (2**attempt))
        return {}

    def append_record(self, target: Path, list_key: str, record: dict[str, Any], schema_name: str | None = None) -> dict[str, Any]:
        def mutator(current: dict[str, Any]) -> dict[str, Any]:
            current.setdefault(list_key, [])
            current.setdefault("schema_version", self.schema_validation_service.get_schema_version(schema_name or ""))
            current[list_key].append(record)
            return current

        return self.mutate_json(target, mutator, schema_name=schema_name)

    def update_record(
        self,
        target: Path,
        list_key: str,
        matcher: Callable[[dict[str, Any]], bool],
        updater: Callable[[dict[str, Any]], dict[str, Any]],
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        def mutator(current: dict[str, Any]) -> dict[str, Any]:
            current.setdefault(list_key, [])
            updated = False
            new_list = []
            for item in current[list_key]:
                if matcher(item):
                    new_list.append(updater(item))
                    updated = True
                else:
                    new_list.append(item)
            if not updated:
                raise ValueError(f"No matching record found in {target}")
            current[list_key] = new_list
            current.setdefault("schema_version", self.schema_validation_service.get_schema_version(schema_name or ""))
            return current

        return self.mutate_json(target, mutator, schema_name=schema_name)

    def delete_record(
        self,
        target: Path,
        list_key: str,
        matcher: Callable[[dict[str, Any]], bool],
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        def mutator(current: dict[str, Any]) -> dict[str, Any]:
            current.setdefault(list_key, [])
            current[list_key] = [item for item in current[list_key] if not matcher(item)]
            current.setdefault("schema_version", self.schema_validation_service.get_schema_version(schema_name or ""))
            return current

        return self.mutate_json(target, mutator, schema_name=schema_name)

    def replace_document(self, target: Path, payload: dict[str, Any], schema_name: str | None = None) -> dict[str, Any]:
        self.safe_write_json(target, payload, schema_name=schema_name)
        return payload
