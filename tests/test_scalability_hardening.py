from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import streamlit as st

from services.alert_engine import AlertEngine
from services.automation_tasks import AutomationTasks
from components.paginated_table import render_paginated_table
from services.cache_service import CacheService
from services.event_bus import EventBus
from services.kpi_service import KPIService
from services.operational_search_service import OperationalSearchService
from services.query_engine import QueryEngine
from services.recommendation_service import RecommendationService
from services.session_state_service import SessionStateService
from tests.helpers.transaction_fixtures import build_runtime
from utils.file_locking import atomic_write_text


def test_session_state_service_round_trip():
    st.session_state.clear()
    service = SessionStateService()
    service.set_active_role("platform_admin")
    service.set_active_order("MO-001")
    service.set_filters("orders", {"status": "OPEN"})
    service.set_navigation("Products")

    assert service.get_active_role() == "platform_admin"
    assert service.get_active_order() == "MO-001"
    assert service.get_filters("orders") == {"status": "OPEN"}
    assert service.get_navigation() == "Products"
    service.clear_context()
    assert service.get_active_role() == ""


def test_cache_service_ttl_and_invalidation(tmp_path):
    path = tmp_path / "data.json"
    atomic_write_text(path, '{"value": 1}')
    cache = CacheService(ttl_seconds=100)
    first = cache.get_json(path, {})
    atomic_write_text(path, '{"value": 2}')
    second = cache.get_json(path, {})
    cache.invalidate("json", str(path))
    third = cache.get_json(path, {})

    assert first["value"] == 1
    assert second["value"] == 1
    assert third["value"] == 2


def test_query_engine_filters_and_paginates():
    rows = [{"id": f"ROW{i:03d}", "status": "OPEN" if i % 2 == 0 else "CLOSED"} for i in range(60)]
    result = QueryEngine().query(rows, status_value="OPEN", page=2, page_size=10)

    assert result["total"] == 30
    assert result["page"] == 2
    assert len(result["rows"]) == 10


def test_atomic_write_text_replaces_file(tmp_path):
    target = tmp_path / "atomic.json"
    atomic_write_text(target, '{"value": 1}')
    atomic_write_text(target, '{"value": 2}')
    assert target.read_text(encoding="utf-8") == '{"value": 2}'


def test_event_bus_triggers_handlers():
    bus = EventBus()
    hits: list[dict] = []
    bus.subscribe("ORDER_CREATED", lambda payload: hits.append(payload))
    bus.publish("ORDER_CREATED", {"order_id": "ORD001"})

    assert hits == [{"order_id": "ORD001"}]


def test_operational_search_rebuilds_index(tmp_path):
    runtime = build_runtime(tmp_path)
    runtime["governance"].register_manufacturer({"manufacturer_code": "MANU101", "business_name": "Search Factory", "status": "ACTIVE"})
    search = OperationalSearchService(index_path=tmp_path / "search_index" / "latest.json", safe_drive_write_service=runtime["safe_write"])
    app_context = {
        "governance_service": runtime["governance"],
        "public_order_service": SimpleNamespace(list_all_orders=lambda: []),
        "ledger_service": SimpleNamespace(list_ledger_entries=lambda _code: []),
    }
    payload = search.rebuild_index(app_context)
    results = search.search(app_context, "search")

    assert payload["records"]
    assert any(item["entity_type"] == "manufacturer" for item in results)


def test_large_dataset_query_simulation():
    rows = [{"id": f"ORD-{i:05d}", "status": "OPEN" if i % 3 == 0 else "CLOSED", "name": f"Product {i}"} for i in range(5000)]
    result = QueryEngine().query(rows, search_query="ORD-000", search_fields=["id"], status_value="OPEN", page=1, page_size=50)

    assert result["total"] > 0
    assert len(result["rows"]) <= 50


def test_pagination_component_renders_current_page(monkeypatch):
    rows = [{"id": f"ROW{i:03d}", "status": "OPEN"} for i in range(30)]
    hits: list[list[dict]] = []

    monkeypatch.setattr("components.paginated_table.st.columns", lambda *_args, **_kwargs: [SimpleNamespace(button=lambda *a, **k: False), SimpleNamespace(button=lambda *a, **k: False), SimpleNamespace(caption=lambda *a, **k: None)])
    monkeypatch.setattr("components.paginated_table.st.dataframe", lambda data, **_kwargs: hits.append(list(data)))
    render_paginated_table(page_key="test_table", rows=rows, search_fields=["id"], status_field="status", page_size=10)

    assert len(hits[0]) == 10


def test_automation_tasks_persist_snapshots_and_publish_events(tmp_path):
    runtime = build_runtime(tmp_path)
    event_bus = EventBus()
    hits: list[dict] = []
    event_bus.subscribe("DAILY_TASKS_COMPLETED", lambda payload: hits.append(payload))
    automation = AutomationTasks(
        runtime_root=tmp_path,
        alert_engine=AlertEngine(alerts_path=tmp_path / "alerts" / "alerts.json", safe_drive_write_service=runtime["safe_write"], json_service=runtime["json_service"], id_allocator_service=runtime["allocator"]),
        recommendation_service=RecommendationService(recommendations_path=tmp_path / "recommendations" / "latest.json", safe_drive_write_service=runtime["safe_write"]),
        kpi_service=KPIService(snapshot_path=tmp_path / "kpis" / "latest.json", safe_drive_write_service=runtime["safe_write"]),
        audit_service=SimpleNamespace(archive_old_logs=lambda keep_days=30: 0),
        safe_drive_write_service=runtime["safe_write"],
        event_bus=event_bus,
    )
    app_context = {
        "governance_service": runtime["governance"],
        "public_order_service": SimpleNamespace(list_all_orders=lambda: [], list_orders_for_seller=lambda _code: []),
        "ledger_service": SimpleNamespace(list_ledger_entries=lambda _code: []),
        "worker_service": SimpleNamespace(list_workers=lambda include_private=False: []),
        "job_service": SimpleNamespace(list_jobs=lambda include_archived=False: [], list_applications=lambda job_id=None: []),
        "inventory_query_service": SimpleNamespace(list_inventory_snapshot=lambda _code: {"items": []}),
        "order_query_service": SimpleNamespace(list_orders=lambda _code: []),
        "procurement_query_service": SimpleNamespace(list_procurement_requests=lambda _code: []),
        "procurement_transaction_service": SimpleNamespace(list_supply_orders=lambda mahajan_id=None: []),
    }
    app_context["alert_engine"] = automation.alert_engine

    result = automation.run_daily_tasks(app_context)

    assert result["task_window"] == "daily"
    assert (tmp_path / "analytics_snapshots" / "daily.json").exists()
    assert hits and hits[0]["task_window"] == "daily"
