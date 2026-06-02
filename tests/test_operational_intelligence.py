from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from services.alert_engine import AlertEngine
from services.automation_tasks import AutomationTasks
from services.audit_service import AuditService
from services.governance_service import GovernanceService
from services.id_allocator_service import IdAllocatorService
from services.job_service import JobService
from services.kpi_service import KPIService
from services.operational_search_service import OperationalSearchService
from services.public_order_service import PublicOrderService
from services.recommendation_service import RecommendationService
from tests.helpers.failure_injector import GmailStub
from tests.helpers.transaction_fixtures import build_procurement_service, build_runtime


def _build_public_order_service(runtime: dict, tmp_path: Path) -> PublicOrderService:
    runtime["governance"].register_manufacturer({"manufacturer_code": "MANU101", "business_name": "Seller", "status": "ACTIVE", "banking": {}})
    return PublicOrderService(
        public_orders_root=tmp_path / "public_orders",
        public_payments_root=tmp_path / "public_payments",
        public_buyer_service=SimpleNamespace(get_by_id=lambda _id: {"public_buyer_id": "BUY001", "email": "buyer@example.com"}, get_by_email=lambda _email: {"public_buyer_id": "BUY001", "email": "buyer@example.com"}),
        public_cart_service=SimpleNamespace(get_cart=lambda _id: {"items": [{"product_id": "PRD1", "qty": 2, "marketplace_price": 60, "mandi_price": 45}], "payment_required": 120, "assigned_seller_manufacturer_id": "MANU101"}, clear_cart=lambda _id: None),
        product_catalog_service=SimpleNamespace(),
        dual_inventory_service=SimpleNamespace(reserve_self_inventory=lambda *_args, **_kwargs: None, finalize_reserved=lambda *_args, **_kwargs: None),
        notification_center_service=SimpleNamespace(create_public_notification=lambda *args, **kwargs: None, create_notification=lambda *args, **kwargs: None),
        gmail_service=GmailStub(),
        governance_service=runtime["governance"],
        safe_drive_write_service=runtime["safe_write"],
        json_service=runtime["json_service"],
        id_allocator_service=runtime["allocator"],
        pricing_service=runtime["pricing"],
        config={},
    )


def _build_app_context(tmp_path: Path) -> dict:
    runtime = build_runtime(tmp_path)
    audit_service = AuditService(log_path=tmp_path / "audit" / "audit.log")
    governance = GovernanceService(tmp_path / "governance", runtime["safe_write"], audit_service=audit_service)
    governance.ensure_files()
    runtime["governance"] = governance
    public_order_service = _build_public_order_service(runtime, tmp_path)
    alert_engine = AlertEngine(alerts_path=tmp_path / "alerts" / "alerts.json", safe_drive_write_service=runtime["safe_write"], json_service=runtime["json_service"], id_allocator_service=runtime["allocator"])
    kpi_service = KPIService(snapshot_path=tmp_path / "kpis" / "latest.json", safe_drive_write_service=runtime["safe_write"])
    recommendation_service = RecommendationService(recommendations_path=tmp_path / "recommendations" / "latest.json", safe_drive_write_service=runtime["safe_write"])
    search_service = OperationalSearchService()
    procurement = build_procurement_service(runtime)
    job_service = JobService(tmp_path / "governance", runtime["safe_write"], runtime["json_service"], runtime["allocator"])
    automation = AutomationTasks(runtime_root=tmp_path, alert_engine=alert_engine, recommendation_service=recommendation_service, kpi_service=kpi_service, audit_service=audit_service)
    return {
        **runtime,
        "audit_service": audit_service,
        "governance_service": governance,
        "public_order_service": public_order_service,
        "procurement_transaction_service": procurement,
        "job_service": job_service,
        "worker_service": SimpleNamespace(list_workers=lambda include_private=False: []),
        "ledger_service": procurement.ledger_service,
        "inventory_query_service": SimpleNamespace(list_inventory_snapshot=lambda _code: {"items": []}),
        "order_query_service": SimpleNamespace(list_orders=lambda _code: []),
        "procurement_query_service": SimpleNamespace(list_procurement_requests=lambda _code: []),
        "alert_engine": alert_engine,
        "kpi_service": kpi_service,
        "recommendation_service": recommendation_service,
        "operational_search_service": search_service,
        "automation_tasks": automation,
    }


def test_alerts_generated_for_low_stock_and_unverified_payment(tmp_path):
    app_context = _build_app_context(tmp_path)
    app_context["governance_service"].upsert_raw_material({"raw_material_id": "RM001", "mahajan_id": "MAH001", "name": "Cotton", "available_qty": 5, "supply_price": 10, "status": "ACTIVE"})
    order = app_context["public_order_service"].create_order_from_cart("BUY001")
    app_context["public_order_service"].submit_payment_reference(order["public_order_id"], "BUY001", payment_reference="UTR123")

    alerts = app_context["alert_engine"].generate_alerts(app_context)
    alert_types = {item["type"] for item in alerts}

    assert "LOW_STOCK" in alert_types
    assert "UNVERIFIED_PAYMENT" in alert_types


def test_kpis_and_health_scores_are_calculated(tmp_path):
    app_context = _build_app_context(tmp_path)
    snapshot = app_context["kpi_service"].calculate_snapshot(app_context)

    assert "marketplace" in snapshot
    assert "mandi" in snapshot
    assert "finance" in snapshot
    assert 0 <= snapshot["health_scores"]["platform"] <= 100


def test_recommendations_generated_for_admin(tmp_path):
    app_context = _build_app_context(tmp_path)
    app_context["governance_service"].upsert_product({"product_id": "PRD001", "name": "Rice", "status": "PROPOSED", "created_at": "2026-05-20T10:00:00+00:00"})
    app_context["alert_engine"].generate_alerts(app_context)

    recommendations = app_context["recommendation_service"].generate(app_context)

    assert "platform_admin" in recommendations
    assert recommendations["platform_admin"]


def test_automation_tasks_run_and_write_outputs(tmp_path):
    app_context = _build_app_context(tmp_path)
    hourly = app_context["automation_tasks"].run_hourly_tasks(app_context)
    daily = app_context["automation_tasks"].run_daily_tasks(app_context)

    assert hourly["task_window"] == "hourly"
    assert daily["task_window"] == "daily"
    assert (tmp_path / "automation" / "hourly.json").exists()
    assert (tmp_path / "automation" / "daily.json").exists()


def test_operational_search_routes_to_expected_pages(tmp_path):
    app_context = _build_app_context(tmp_path)
    app_context["governance_service"].register_manufacturer({"manufacturer_code": "MANU999", "business_name": "Search Factory", "status": "ACTIVE"})
    app_context["governance_service"].upsert_raw_material({"raw_material_id": "RMSEARCH", "mahajan_id": "MAH001", "name": "Search Cotton", "available_qty": 25, "supply_price": 12, "status": "ACTIVE"})

    results = app_context["operational_search_service"].search(app_context, "search")

    assert any(item["entity_type"] == "manufacturer" and item["target"]["route"] == "Manufacturers" for item in results)
    assert any(item["entity_type"] == "raw_material" and item["target"]["route"] == "Raw Materials" for item in results)


def test_jobs_lifecycle_supports_pause_close_and_archive(tmp_path):
    runtime = build_runtime(tmp_path)
    job_service = JobService(tmp_path / "governance", runtime["safe_write"], runtime["json_service"], runtime["allocator"])
    job = job_service.create_job(
        manufacturer_id="MANU101",
        title="Packaging Helper",
        work_type="Daily Wage",
        worker_count=2,
        city="Pune",
        area="Bhosari",
        pay_type="daily",
        pay_amount=800,
        shift_time="9AM-6PM",
        skills_required=["Packing"],
        description="Need two workers",
        manufacturer_contact_email="owner@example.com",
    )

    paused = job_service.update_job_lifecycle(job_id=job["job_id"], lifecycle_status="PAUSED")
    archived = job_service.update_job_lifecycle(job_id=job["job_id"], lifecycle_status="ARCHIVED")

    assert paused["lifecycle_status"] == "PAUSED"
    assert archived["lifecycle_status"] == "ARCHIVED"


def test_audit_service_supports_severity_filters(tmp_path):
    audit = AuditService(log_path=tmp_path / "audit" / "audit.log")
    audit.log_governance_event(actor="admin@example.com", role="platform_admin", action="TEST", entity_type="order", entity_id="ORD001", details={"severity": "CRITICAL"})
    audit.log_governance_event(actor="user@example.com", role="manufacturer", action="TEST", entity_type="order", entity_id="ORD002", details={"severity": "LOW"})

    rows = audit.read_structured_events(severity="CRITICAL")

    assert len(rows) == 1
    assert rows[0]["entity_id"] == "ORD001"
