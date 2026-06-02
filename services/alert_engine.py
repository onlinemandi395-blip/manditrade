from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class AlertEngine:
    def __init__(self, *, alerts_path: Path, safe_drive_write_service, json_service, id_allocator_service) -> None:
        self.alerts_path = alerts_path
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service

    def ensure_file(self) -> None:
        if not self.alerts_path.exists():
            self.safe_drive_write_service.replace_document(self.alerts_path, {"schema_version": "1.0", "alerts": []})

    def list_alerts(self, *, resolved: bool | None = None, severity: str = "", entity_type: str = "") -> list[dict[str, Any]]:
        self.ensure_file()
        rows = self.json_service.read_json(self.alerts_path, {"alerts": []}).get("alerts", [])
        if resolved is not None:
            rows = [item for item in rows if bool(item.get("resolved", False)) is resolved]
        if severity:
            rows = [item for item in rows if str(item.get("severity", "")).upper() == severity.strip().upper()]
        if entity_type:
            rows = [item for item in rows if str(item.get("entity_type", "")).lower() == entity_type.strip().lower()]
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows

    def resolve_alert(self, alert_id: str) -> dict[str, Any]:
        self.ensure_file()
        updated: dict[str, Any] | None = None

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal updated
            for item in payload.get("alerts", []):
                if item.get("alert_id") == alert_id:
                    item["resolved"] = True
                    item["resolved_at"] = datetime.now(UTC).isoformat()
                    updated = dict(item)
                    return payload
            raise ValueError(f"Alert not found: {alert_id}")

        self.safe_drive_write_service.mutate_json(self.alerts_path, mutator)
        return updated or {}

    def generate_alerts(self, app_context: dict) -> list[dict[str, Any]]:
        self.ensure_file()
        generated: list[dict[str, Any]] = []
        governance = app_context["governance_service"]
        public_order_service = app_context["public_order_service"]
        procurement_service = app_context["procurement_transaction_service"]
        job_service = app_context["job_service"]
        ledger_service = app_context["ledger_service"]

        now = datetime.now(UTC)
        for material in governance.list_raw_materials():
            if str(material.get("status", "")).upper() == "ACTIVE" and int(material.get("available_qty", 0) or 0) <= 10:
                generated.append(self._build_alert("HIGH", "LOW_STOCK", "raw_material", material.get("raw_material_id", ""), f"Raw material {material.get('name', material.get('raw_material_id', ''))} is low on stock."))
        for manufacturer in governance.list_manufacturers():
            if str(manufacturer.get("status", "")).upper() in {"INACTIVE", "ARCHIVED", "BLOCKED"}:
                generated.append(self._build_alert("MEDIUM", "INACTIVE_MANUFACTURER", "manufacturer", manufacturer.get("manufacturer_code", ""), f"Manufacturer {manufacturer.get('business_name', manufacturer.get('manufacturer_code', ''))} is inactive."))
        for mahajan in governance.list_mahajans():
            if str(mahajan.get("status", "")).upper() in {"INACTIVE", "ARCHIVED"}:
                generated.append(self._build_alert("MEDIUM", "INACTIVE_MAHAJAN", "mahajan", mahajan.get("mahajan_id", ""), f"Mahajan {mahajan.get('business_name', mahajan.get('mahajan_id', ''))} is inactive."))
        for order in public_order_service.list_all_orders():
            if str(order.get("payment_status", "")).upper() == "SUBMITTED":
                generated.append(self._build_alert("HIGH", "UNVERIFIED_PAYMENT", "public_order", order.get("public_order_id", ""), f"Marketplace payment for {order.get('public_order_id', '')} is awaiting verification."))
            if str(order.get("status", "")).upper() == "CONFIRMED" and self._hours_since(order.get("updated_at", ""), now) >= 24:
                generated.append(self._build_alert("HIGH", "DELAYED_DISPATCH", "public_order", order.get("public_order_id", ""), f"Marketplace order {order.get('public_order_id', '')} is confirmed but not dispatched."))
            if str(order.get("status", "")).upper() == "DISPATCHED" and not str((order.get("logistics") or {}).get("vehicle_number", "")).strip():
                generated.append(self._build_alert("CRITICAL", "FAILED_LOGISTICS_UPDATE", "public_order", order.get("public_order_id", ""), f"Marketplace order {order.get('public_order_id', '')} is dispatched without logistics details."))
        for order in procurement_service.list_supply_orders():
            status = str(order.get("status", "")).upper()
            if status in {"REQUESTED_BY_MANUFACTURER", "SENT_TO_MAHAJAN", "ADMIN_PRICE_SET", "MANUFACTURER_CONFIRMED"} and self._hours_since(order.get("updated_at", order.get("created_at", "")), now) >= 48:
                generated.append(self._build_alert("HIGH", "STALLED_MANDI_ORDER", "supply_order", order.get("mandi_order_id", ""), f"Mandi order {order.get('mandi_order_id', '')} is stalled in {status}."))
            if status == "MANUFACTURER_CONFIRMED" and self._hours_since(order.get("updated_at", ""), now) >= 24:
                generated.append(self._build_alert("HIGH", "DELAYED_DISPATCH", "supply_order", order.get("mandi_order_id", ""), f"Supply order {order.get('mandi_order_id', '')} is awaiting dispatch update."))
            if status == "MAHAJAN_DISPATCHED" and not str((order.get("logistics") or {}).get("vehicle_number", "")).strip():
                generated.append(self._build_alert("CRITICAL", "FAILED_LOGISTICS_UPDATE", "supply_order", order.get("mandi_order_id", ""), f"Supply order {order.get('mandi_order_id', '')} is dispatched without vehicle details."))
        for product in governance.list_products():
            if str(product.get("status", "")).upper() == "PROPOSED" and self._hours_since(product.get("created_at", ""), now) >= 72:
                generated.append(self._build_alert("MEDIUM", "PENDING_APPROVAL_TOO_LONG", "product", product.get("product_id", ""), f"Product proposal {product.get('product_id', '')} is pending too long."))
        for manufacturer in governance.list_manufacturers():
            for entry in ledger_service.list_ledger_entries(manufacturer.get("manufacturer_code", "")):
                if str(entry.get("status", "")).upper() == "OVERDUE":
                    severity = "CRITICAL" if float(entry.get("balance_due", 0) or 0) >= 10000 else "HIGH"
                    generated.append(self._build_alert(severity, "OVERDUE_PAYMENT", "ledger_entry", entry.get("entry_id", ""), f"Ledger entry {entry.get('entry_id', '')} is overdue."))
        for job in job_service.list_jobs():
            if str(job.get("lifecycle_status", "ACTIVE")).upper() == "ACTIVE" and self._hours_since(job.get("created_at", ""), now) >= 168 and not job_service.list_applications(job_id=job.get("job_id", "")):
                generated.append(self._build_alert("LOW", "STALE_JOB", "job", job.get("job_id", ""), f"Job {job.get('job_id', '')} has no applications for a week."))
        return self._persist_generated_alerts(generated)

    def read_snapshot(self) -> dict[str, Any]:
        self.ensure_file()
        alerts = self.list_alerts()
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "total_alerts": len(alerts),
            "open_alerts": len([item for item in alerts if not item.get("resolved", False)]),
            "critical_alerts": len([item for item in alerts if str(item.get("severity", "")).upper() == "CRITICAL" and not item.get("resolved", False)]),
        }

    def _persist_generated_alerts(self, generated: list[dict[str, Any]]) -> list[dict[str, Any]]:
        existing = self.list_alerts()
        existing_index = {
            (str(item.get("type", "")).upper(), str(item.get("entity_type", "")).lower(), str(item.get("entity_id", "")), bool(item.get("resolved", False))): item
            for item in existing
        }
        payload = {"schema_version": "1.0", "alerts": existing}
        new_rows: list[dict[str, Any]] = []
        for alert in generated:
            key = (str(alert.get("type", "")).upper(), str(alert.get("entity_type", "")).lower(), str(alert.get("entity_id", "")), False)
            if key in existing_index:
                continue
            payload["alerts"].append(alert)
            new_rows.append(alert)
        self.safe_drive_write_service.replace_document(self.alerts_path, payload)
        return new_rows

    def _build_alert(self, severity: str, alert_type: str, entity_type: str, entity_id: str, message: str) -> dict[str, Any]:
        return {
            "alert_id": self.id_allocator_service.allocate("alert"),
            "severity": severity,
            "type": alert_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id or ""),
            "message": message,
            "created_at": datetime.now(UTC).isoformat(),
            "resolved": False,
        }

    def _hours_since(self, value: str, now: datetime) -> float:
        if not value:
            return 0
        try:
            then = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return 0
        if then.tzinfo is None:
            then = then.replace(tzinfo=UTC)
        return (now - then).total_seconds() / 3600
