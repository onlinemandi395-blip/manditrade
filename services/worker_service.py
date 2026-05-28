from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class WorkerService:
    def __init__(self, governance_root: Path, safe_drive_write_service, json_service, id_allocator_service) -> None:
        self.governance_root = governance_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service

    @property
    def workers_path(self) -> Path:
        return self.governance_root / "workers.json"

    def ensure_file(self) -> None:
        if not self.workers_path.exists():
            self.safe_drive_write_service.replace_document(
                self.workers_path,
                {"schema_version": "2.0", "workers": []},
            )

    def list_workers(self, *, include_private: bool = False) -> list[dict[str, Any]]:
        self.ensure_file()
        workers = self.json_service.read_json(self.workers_path, {"workers": []}).get("workers", [])
        if include_private:
            return workers
        public_workers = []
        for worker in workers:
            if not worker.get("public_profile_opt_in", False):
                continue
            public_workers.append(
                {
                    "worker_id": worker.get("worker_id"),
                    "name": worker.get("name"),
                    "city": worker.get("city"),
                    "area": worker.get("area"),
                    "skills": worker.get("skills", []),
                    "preferred_work_type": worker.get("preferred_work_type", []),
                    "available": worker.get("available", False),
                    "status": worker.get("status", "ACTIVE"),
                }
            )
        return public_workers

    def get_worker_by_email(self, email: str) -> dict[str, Any] | None:
        self.ensure_file()
        workers = self.json_service.read_json(self.workers_path, {"workers": []}).get("workers", [])
        email_key = email.strip().lower()
        return next((item for item in workers if item.get("linked_email", "").strip().lower() == email_key), None)

    def upsert_worker(
        self,
        *,
        linked_email: str,
        name: str,
        mobile: str,
        city: str,
        area: str,
        skills: list[str],
        preferred_work_type: list[str],
        available: bool,
        public_profile_opt_in: bool,
    ) -> dict[str, Any]:
        self.ensure_file()
        payload = self.json_service.read_json(self.workers_path, {"workers": []})
        linked_email_key = linked_email.strip().lower()
        existing = next((item for item in payload.get("workers", []) if item.get("linked_email", "").strip().lower() == linked_email_key), None)
        if existing is None:
            existing = {
                "worker_id": self.id_allocator_service.allocate("worker"),
                "status": "ACTIVE",
                "created_at": datetime.now(UTC).isoformat(),
            }
            payload["workers"].append(existing)
        existing.update(
            {
                "linked_email": linked_email_key,
                "name": name.strip(),
                "mobile": mobile.strip(),
                "city": city.strip(),
                "area": area.strip(),
                "skills": [item.strip() for item in skills if item.strip()],
                "preferred_work_type": [item.strip() for item in preferred_work_type if item.strip()],
                "available": bool(available),
                "public_profile_opt_in": bool(public_profile_opt_in),
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        self.safe_drive_write_service.replace_document(self.workers_path, payload)
        return existing
