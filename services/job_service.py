from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class JobService:
    def __init__(
        self,
        governance_root: Path,
        safe_drive_write_service,
        json_service,
        id_allocator_service,
        notification_center_service=None,
        ledger_service=None,
        gmail_service=None,
    ) -> None:
        self.governance_root = governance_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service
        self.notification_center_service = notification_center_service
        self.ledger_service = ledger_service
        self.gmail_service = gmail_service

    @property
    def jobs_path(self) -> Path:
        return self.governance_root / "jobs.json"

    def ensure_file(self) -> None:
        if not self.jobs_path.exists():
            self.safe_drive_write_service.replace_document(
                self.jobs_path,
                {"schema_version": "2.0", "jobs": [], "applications": []},
            )

    def list_jobs(self, *, manufacturer_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        self.ensure_file()
        jobs = self.json_service.read_json(self.jobs_path, {"jobs": []}).get("jobs", [])
        if manufacturer_id:
            jobs = [item for item in jobs if item.get("manufacturer_id") == manufacturer_id]
        if status:
            jobs = [item for item in jobs if item.get("status") == status]
        return jobs

    def list_open_jobs(self) -> list[dict[str, Any]]:
        return self.list_jobs(status="OPEN")

    def list_applications(self, *, job_id: str | None = None, worker_id: str | None = None, manufacturer_id: str | None = None) -> list[dict[str, Any]]:
        self.ensure_file()
        payload = self.json_service.read_json(self.jobs_path, {"jobs": [], "applications": []})
        applications = payload.get("applications", [])
        if job_id:
            applications = [item for item in applications if item.get("job_id") == job_id]
        if worker_id:
            applications = [item for item in applications if item.get("worker_id") == worker_id]
        if manufacturer_id:
            manufacturer_job_ids = {job.get("job_id") for job in payload.get("jobs", []) if job.get("manufacturer_id") == manufacturer_id}
            applications = [item for item in applications if item.get("job_id") in manufacturer_job_ids]
        return applications

    def create_job(
        self,
        *,
        manufacturer_id: str,
        title: str,
        work_type: str,
        worker_count: int,
        city: str,
        area: str,
        pay_type: str,
        pay_amount: float,
        shift_time: str,
        skills_required: list[str],
        description: str,
        manufacturer_contact_email: str = "",
    ) -> dict[str, Any]:
        self.ensure_file()
        job = {
            "job_id": self.id_allocator_service.allocate("job"),
            "manufacturer_id": manufacturer_id,
            "title": title.strip(),
            "work_type": work_type.strip(),
            "worker_count": int(worker_count),
            "location": {"city": city.strip(), "area": area.strip()},
            "pay_type": pay_type.strip(),
            "pay_amount": float(pay_amount),
            "shift_time": shift_time.strip(),
            "skills_required": [item.strip() for item in skills_required if item.strip()],
            "description": description.strip(),
            "manufacturer_contact_email": manufacturer_contact_email.strip().lower(),
            "status": "OPEN",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.safe_drive_write_service.append_record(self.jobs_path, "jobs", job)
        return job

    def apply_to_job(self, *, job_id: str, worker_id: str, worker_note: str, worker_contact_email: str = "") -> dict[str, Any]:
        self.ensure_file()
        payload = self.json_service.read_json(self.jobs_path, {"jobs": [], "applications": []})
        job = next((item for item in payload.get("jobs", []) if item.get("job_id") == job_id), None)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        if job.get("status") not in {"OPEN", "APPLICATIONS_RECEIVED"}:
            raise ValueError("Job is not open for applications.")
        existing = next((item for item in payload.get("applications", []) if item.get("job_id") == job_id and item.get("worker_id") == worker_id), None)
        if existing:
            raise ValueError("Worker already applied to this job.")
        application = {
            "application_id": self.id_allocator_service.allocate("application"),
            "job_id": job_id,
            "worker_id": worker_id,
            "status": "APPLIED",
            "worker_note": worker_note.strip(),
            "worker_contact_email": worker_contact_email.strip().lower(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        job["status"] = "APPLICATIONS_RECEIVED"
        payload["applications"].append(application)
        self.safe_drive_write_service.replace_document(self.jobs_path, payload)
        if self.notification_center_service:
            self.notification_center_service.create_notification(
                job["manufacturer_id"],
                user_id=job["manufacturer_id"],
                notification_type="JOB_APPLICATION_RECEIVED",
                priority="HIGH",
                title="Job Application Received",
                message=f"Worker {worker_id} applied for {job['title']}.",
                source_type="JOB",
                source_id=job_id,
            )
        if self.gmail_service and job.get("manufacturer_contact_email"):
            self.gmail_service.enqueue_message(
                job["manufacturer_contact_email"],
                f"New job application for {job['title']}",
                f"Worker {worker_id} applied to job {job['job_id']}. Note: {worker_note.strip() or 'No note provided.'}",
                "job_application_received",
            )
        return application

    def update_application_status(self, *, job_id: str, application_id: str, next_status: str) -> dict[str, Any]:
        self.ensure_file()
        payload = self.json_service.read_json(self.jobs_path, {"jobs": [], "applications": []})
        job = next((item for item in payload.get("jobs", []) if item.get("job_id") == job_id), None)
        application = next((item for item in payload.get("applications", []) if item.get("application_id") == application_id), None)
        if job is None or application is None:
            raise ValueError("Job application not found.")
        application["status"] = next_status
        application["updated_at"] = datetime.now(UTC).isoformat()
        if next_status == "ACCEPTED":
            job["status"] = "WORKER_ACCEPTED"
        elif next_status == "WORKER_CONFIRMED":
            job["status"] = "IN_PROGRESS"
        elif next_status == "COMPLETED":
            job["status"] = "COMPLETED"
        self.safe_drive_write_service.replace_document(self.jobs_path, payload)
        if self.gmail_service and application.get("worker_contact_email"):
            self.gmail_service.enqueue_message(
                application["worker_contact_email"],
                f"Job update: {job['title']}",
                f"Your application {application_id} is now {next_status} for job {job['job_id']}.",
                "job_application_status",
            )
        if self.notification_center_service and next_status in {"ACCEPTED", "WORKER_CONFIRMED", "COMPLETED"}:
            self.notification_center_service.create_notification(
                job["manufacturer_id"],
                user_id=application["worker_id"],
                notification_type=f"JOB_{next_status}",
                priority="HIGH" if next_status == "ACCEPTED" else "PENDING",
                title="Job Application Updated",
                message=f"Application {application_id} moved to {next_status}.",
                source_type="JOB",
                source_id=job_id,
            )
        return application

    def complete_job(self, *, job_id: str, application_id: str, manufacturer_id: str, worker_id: str, unpaid_amount: float = 0.0, note: str = "") -> dict[str, Any]:
        application = self.update_application_status(job_id=job_id, application_id=application_id, next_status="COMPLETED")
        if unpaid_amount > 0 and self.ledger_service:
            self.ledger_service.create_entry(
                manufacturer_id,
                party_a=manufacturer_id,
                party_b=worker_id,
                entry_type="JOB_PAYMENT_DUE",
                amount=float(unpaid_amount),
                paid_amount=0.0,
                ledger_days=0,
                note=note or "Worker payment pending after job completion.",
            )
        return application
