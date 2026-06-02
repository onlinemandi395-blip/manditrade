from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from components.timeline import get_timeline_step_states
from services.audit_service import AuditService
from services.governance_service import GovernanceService
from services.public_order_service import PublicOrderService
from tests.helpers.failure_injector import GmailStub
from tests.helpers.transaction_fixtures import build_runtime
from utils.deep_links import build_deep_link_target
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.filtering import filter_records
from utils.status_styles import get_status_style


def test_filter_records_search_and_status_are_safe():
    rows = [
        {"order_id": "MO-001", "status": "OPEN", "amount": 100, "owner": "MANU101"},
        {"order_id": "MO-002", "status": "CLOSED", "amount": 250, "owner": "MANU202"},
    ]

    filtered = filter_records(rows, search_query="MO-001", search_fields=["order_id"], status_value="OPEN", price_field="amount", min_price=50)

    assert filtered == [rows[0]]


def test_timeline_step_states_cover_current_status():
    steps = ["REQUESTED", "QUOTED", "DISPATCHED", "CLOSED"]
    states = get_timeline_step_states("DISPATCHED", steps)

    assert states[0]["is_complete"] is True
    assert states[2]["is_current"] is True
    assert states[3]["is_complete"] is False


def test_status_styles_are_centralized():
    assert get_status_style("PENDING")["tone"] == "warning"
    assert get_status_style("CLOSED")["tone"] == "success"
    assert get_status_style("ARCHIVED")["tone"] == "muted"


def test_deep_link_target_maps_notifications_to_routes():
    assert build_deep_link_target("PUBLIC_ORDER", "PO-001")["route"] == "Marketplace Orders"
    assert build_deep_link_target("SUPPLY_ORDER", "MO-001")["route"] == "Mandi Orders"
    assert build_deep_link_target("JOB", "JOB-001")["route"] == "Jobs"


def test_export_utilities_return_bytes():
    rows = [{"id": "A1", "status": "OPEN"}]

    csv_bytes = export_rows_to_csv_bytes(rows)
    json_bytes = export_rows_to_json_bytes(rows)

    assert b"id,status" in csv_bytes
    assert b'"id": "A1"' in json_bytes


def test_governance_delete_archives_records_and_writes_audit_log(tmp_path):
    runtime = build_runtime(tmp_path)
    audit = AuditService(log_path=tmp_path / "audit" / "audit.log")
    governance = GovernanceService(tmp_path / "governance", runtime["safe_write"], audit_service=audit)
    governance.ensure_files()
    governance.upsert_mahajan(
        {
            "mahajan_id": "MAH001",
            "business_name": "Supply House",
            "owner_name": "Aakash",
            "email": "mahajan@example.com",
            "status": "ACTIVE",
        }
    )

    governance.delete_mahajan("MAH001")

    assert governance.get_mahajan("MAH001")["status"] == "ARCHIVED"
    audit_files = list((tmp_path / "audit" / "audit_logs").glob("*.jsonl"))
    assert audit_files
    assert "ARCHIVE_MAHAJAN" in audit_files[0].read_text(encoding="utf-8")


def test_public_order_logistics_update_persists(tmp_path):
    runtime = build_runtime(tmp_path)
    public_buyer_root = tmp_path / "public_buyers"
    public_order_root = tmp_path / "public_orders"
    public_payment_root = tmp_path / "public_payments"
    public_buyer_root.mkdir(parents=True, exist_ok=True)
    runtime["governance"].register_manufacturer({"manufacturer_code": "MANU101", "business_name": "Seller", "status": "ACTIVE"})
    service = PublicOrderService(
        public_orders_root=public_order_root,
        public_payments_root=public_payment_root,
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
    order = service.create_order_from_cart("BUY001")

    updated = service.update_logistics(
        order["public_order_id"],
        actor=SimpleNamespace(role="platform_admin", manufacturer_code="", email="admin@example.com"),
        transport_mode="Road",
        driver_name="Ramesh",
        vehicle_number="MH12AB1234",
        delivery_status="READY_FOR_DISPATCH",
    )

    assert updated["logistics"]["transport_mode"] == "Road"
    assert updated["logistics"]["driver_name"] == "Ramesh"
    assert updated["logistics"]["vehicle_number"] == "MH12AB1234"
    assert updated["logistics"]["delivery_status"] == "READY_FOR_DISPATCH"
