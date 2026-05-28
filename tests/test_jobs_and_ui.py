from __future__ import annotations

from components.ui_shell import render_action_card, render_metric_card, render_mobile_record_card, render_status_badge
from services.job_service import JobService
from services.ledger_service import LedgerService
from services.notification_center_service import NotificationCenterService
from services.worker_service import WorkerService
from tests.helpers.failure_injector import GmailStub
from tests.helpers.transaction_fixtures import build_runtime


def build_job_stack(tmp_path):
    runtime = build_runtime(tmp_path)
    runtime["drive"].get_manufacturer_paths("MANU101")
    notification_center = NotificationCenterService(runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    ledger_service = LedgerService(runtime["safe_write"], runtime["json_service"], runtime["allocator"], runtime["domain_paths"])
    gmail_service = GmailStub()
    worker_service = WorkerService(tmp_path / "governance", runtime["safe_write"], runtime["json_service"], runtime["allocator"])
    job_service = JobService(
        governance_root=tmp_path / "governance",
        safe_drive_write_service=runtime["safe_write"],
        json_service=runtime["json_service"],
        id_allocator_service=runtime["allocator"],
        notification_center_service=notification_center,
        ledger_service=ledger_service,
        gmail_service=gmail_service,
    )
    return runtime, worker_service, job_service, gmail_service, ledger_service


def test_worker_profile_and_job_application_flow(tmp_path):
    _runtime, worker_service, job_service, gmail_service, _ledger_service = build_job_stack(tmp_path)
    worker = worker_service.upsert_worker(
        linked_email="worker@example.com",
        name="Ravi Kumar",
        mobile="9999999999",
        city="Pune",
        area="Bhosari",
        skills=["Loading", "Packaging"],
        preferred_work_type=["Daily Wage", "Part-time"],
        available=True,
        public_profile_opt_in=True,
    )
    job = job_service.create_job(
        manufacturer_id="MANU101",
        title="Packaging Helper",
        work_type="Daily Wage",
        worker_count=3,
        city="Pune",
        area="Bhosari",
        pay_type="daily",
        pay_amount=800,
        shift_time="9AM-6PM",
        skills_required=["Packaging", "Loading"],
        description="Need urgent packaging workers for 2 days",
        manufacturer_contact_email="owner@example.com",
    )
    application = job_service.apply_to_job(
        job_id=job["job_id"],
        worker_id=worker["worker_id"],
        worker_note="Available from tomorrow morning",
        worker_contact_email="worker@example.com",
    )
    updated = job_service.update_application_status(
        job_id=job["job_id"],
        application_id=application["application_id"],
        next_status="ACCEPTED",
    )

    assert application["status"] == "APPLIED"
    assert updated["status"] == "ACCEPTED"
    assert len(job_service.list_open_jobs()) == 0
    assert gmail_service.sent[0]["notification_type"] == "job_application_received"
    assert gmail_service.sent[1]["notification_type"] == "job_application_status"


def test_job_completion_creates_worker_ledger_entry_when_unpaid(tmp_path):
    _runtime, worker_service, job_service, _gmail_service, ledger_service = build_job_stack(tmp_path)
    worker = worker_service.upsert_worker(
        linked_email="worker@example.com",
        name="Ravi Kumar",
        mobile="9999999999",
        city="Pune",
        area="Bhosari",
        skills=["Loading"],
        preferred_work_type=["Daily Wage"],
        available=True,
        public_profile_opt_in=True,
    )
    job = job_service.create_job(
        manufacturer_id="MANU101",
        title="Loading Helper",
        work_type="Shift-based",
        worker_count=1,
        city="Pune",
        area="Market Yard",
        pay_type="shift",
        pay_amount=600,
        shift_time="6AM-2PM",
        skills_required=["Loading"],
        description="Morning unloading shift",
        manufacturer_contact_email="owner@example.com",
    )
    application = job_service.apply_to_job(
        job_id=job["job_id"],
        worker_id=worker["worker_id"],
        worker_note="Can join",
        worker_contact_email="worker@example.com",
    )
    job_service.complete_job(
        job_id=job["job_id"],
        application_id=application["application_id"],
        manufacturer_id="MANU101",
        worker_id=worker["worker_id"],
        unpaid_amount=600.0,
        note="Daily wage to settle by evening.",
    )
    ledgers = ledger_service.list_ledgers("MANU101")
    assert ledgers[0]["entries"][0]["entry_type"] == "JOB_PAYMENT_DUE"
    assert ledgers[0]["entries"][0]["balance_due"] == 600.0


def test_ui_helpers_return_stable_html_fragments():
    metric_html = render_metric_card("Open Jobs", "12", "OPEN")
    badge_html = render_status_badge("HIGH_PRIORITY")
    action_html = render_action_card("Review Applications", "2 workers are waiting for approval.", "Open jobs")
    record_html = render_mobile_record_card({"job_id": "JOB-2026-000001", "status": "OPEN"})

    assert "mt-card--metric" in metric_html
    assert "mt-badge-high-priority" in badge_html
    assert "Review Applications" in action_html
    assert "JOB-2026-000001" in record_html
