from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class KPIService:
    def __init__(self, *, snapshot_path: Path, safe_drive_write_service) -> None:
        self.snapshot_path = snapshot_path
        self.safe_drive_write_service = safe_drive_write_service

    def calculate_snapshot(self, app_context: dict) -> dict[str, Any]:
        governance = app_context["governance_service"]
        public_orders = app_context["public_order_service"].list_all_orders()
        supply_orders = governance.list_supply_orders()
        jobs = app_context["job_service"].list_jobs()
        workers = app_context["worker_service"].list_workers(include_private=True)
        manufacturers = governance.list_manufacturers()

        today = datetime.now(UTC).date().isoformat()
        marketplace_today = [item for item in public_orders if str(item.get("created_at", ""))[:10] == today]
        revenue_today = round(sum(float(item.get("total_amount", 0) or 0) for item in marketplace_today), 2)
        active_mandi = [item for item in supply_orders if str(item.get("status", "")).upper() not in {"CLOSED", "CANCELLED"}]
        avg_fulfillment_hours = self._average_hours_between_status(supply_orders, "REQUESTED_BY_MANUFACTURER", "MANUFACTURER_RECEIVED")
        supplier_response_hours = self._average_hours_between_status(supply_orders, "REQUESTED_BY_MANUFACTURER", "MAHAJAN_QUOTED")
        delayed_delivery_pct = round((len([item for item in supply_orders if str(item.get("status", "")).upper() == "MANUFACTURER_CONFIRMED"]) / max(len(active_mandi), 1)) * 100, 2)
        outstanding_ledger = 0.0
        overdue_entries = 0
        total_entries = 0
        for manufacturer in manufacturers:
            for entry in app_context["ledger_service"].list_ledger_entries(manufacturer.get("manufacturer_code", "")):
                total_entries += 1
                outstanding_ledger += float(entry.get("balance_due", 0) or 0)
                if str(entry.get("status", "")).upper() == "OVERDUE":
                    overdue_entries += 1
        supply_ledgers = governance.list_supply_ledger_entries()
        commission_pending = round(sum(float(item.get("mahajan_transaction_fee", 0) or 0) for item in supply_ledgers if str(item.get("commission_status", "")).upper() != "PAID"), 2)
        top_products = Counter()
        for order in public_orders:
            for item in order.get("items", []):
                top_products[str(item.get("product_name", item.get("product_id", "")))] += int(item.get("qty", 0) or 0)
        top_raw_materials = Counter(str(item.get("raw_material_id", "")) for item in supply_orders if item.get("raw_material_id"))
        snapshot = {
            "generated_at": datetime.now(UTC).isoformat(),
            "marketplace": {
                "orders_today": len(marketplace_today),
                "revenue_today": revenue_today,
                "conversion_count": len([item for item in public_orders if str(item.get("payment_status", "")).upper() == "VERIFIED"]),
            },
            "mandi": {
                "active_orders": len(active_mandi),
                "average_fulfillment_hours": avg_fulfillment_hours,
                "supplier_response_hours": supplier_response_hours,
            },
            "supply": {
                "dispatch_rate": round((len([item for item in supply_orders if str(item.get("status", "")).upper() in {"MAHAJAN_DISPATCHED", "MANUFACTURER_RECEIVED", "CLOSED"}]) / max(len(supply_orders), 1)) * 100, 2),
                "delayed_delivery_percent": delayed_delivery_pct,
                "low_stock_frequency": len([item for item in governance.list_raw_materials() if int(item.get("available_qty", 0) or 0) <= 10]),
            },
            "finance": {
                "outstanding_ledger": round(outstanding_ledger, 2),
                "overdue_percent": round((overdue_entries / max(total_entries, 1)) * 100, 2),
                "commission_pending": commission_pending,
            },
            "workforce": {
                "jobs_filled": len([item for item in jobs if str(item.get("status", "")).upper() == "COMPLETED"]),
                "worker_response_rate": round((len(app_context["job_service"].list_applications()) / max(len(jobs), 1)) * 100, 2),
                "inactive_workers": len([item for item in workers if str(item.get("status", "")).upper() != "ACTIVE" or not bool(item.get("available", False))]),
            },
            "tops": {
                "manufacturers": [item.get("manufacturer_code", "") for item in manufacturers[:5]],
                "products": [{"name": key, "qty": value} for key, value in top_products.most_common(5)],
                "raw_materials": [{"raw_material_id": key, "count": value} for key, value in top_raw_materials.most_common(5)],
            },
            "health_scores": {
                "platform": self.calculate_platform_health_score(app_context),
                "manufacturers": {item.get("manufacturer_code", ""): self.calculate_manufacturer_health_score(app_context, item.get("manufacturer_code", "")) for item in manufacturers if item.get("manufacturer_code")},
                "mahajans": {item.get("mahajan_id", ""): self.calculate_mahajan_health_score(app_context, item.get("mahajan_id", "")) for item in governance.list_mahajans() if item.get("mahajan_id")},
            },
        }
        self.safe_drive_write_service.replace_document(self.snapshot_path, snapshot)
        return snapshot

    def calculate_manufacturer_health_score(self, app_context: dict, manufacturer_code: str) -> int:
        inventory = app_context["inventory_query_service"].list_inventory_snapshot(manufacturer_code)
        entries = app_context["ledger_service"].list_ledger_entries(manufacturer_code)
        public_orders = app_context["public_order_service"].list_orders_for_seller(manufacturer_code)
        score = 100
        if not inventory.get("items"):
            score -= 20
        score -= 10 * len([item for item in entries if str(item.get("status", "")).upper() == "OVERDUE"])
        score -= 5 * len([item for item in public_orders if str(item.get("status", "")).upper() == "CONFIRMED"])
        return max(0, min(100, score))

    def calculate_mahajan_health_score(self, app_context: dict, mahajan_id: str) -> int:
        orders = app_context["procurement_transaction_service"].list_supply_orders(mahajan_id=mahajan_id)
        score = 100
        score -= 10 * len([item for item in orders if str(item.get("status", "")).upper() == "SENT_TO_MAHAJAN"])
        score -= 8 * len([item for item in orders if str(item.get("status", "")).upper() == "MANUFACTURER_CONFIRMED"])
        if not orders:
            score -= 10
        return max(0, min(100, score))

    def calculate_platform_health_score(self, app_context: dict) -> int:
        alerts = app_context["alert_engine"].list_alerts(resolved=False)
        overdue = 0
        for manufacturer in app_context["governance_service"].list_manufacturers():
            overdue += len([item for item in app_context["ledger_service"].list_ledger_entries(manufacturer.get("manufacturer_code", "")) if str(item.get("status", "")).upper() == "OVERDUE"])
        score = 100 - (5 * len([item for item in alerts if str(item.get("severity", "")).upper() == "HIGH"])) - (10 * len([item for item in alerts if str(item.get("severity", "")).upper() == "CRITICAL"])) - (3 * overdue)
        return max(0, min(100, score))

    def _average_hours_between_status(self, orders: list[dict[str, Any]], start_status: str, end_status: str) -> float:
        durations: list[float] = []
        for order in orders:
            history = list(order.get("internal_status_history", []))
            start = next((item for item in history if item.get("status") == start_status), None)
            end = next((item for item in history if item.get("status") == end_status), None)
            if not start or not end:
                continue
            try:
                start_at = datetime.fromisoformat(str(start.get("at", "")).replace("Z", "+00:00"))
                end_at = datetime.fromisoformat(str(end.get("at", "")).replace("Z", "+00:00"))
            except ValueError:
                continue
            durations.append((end_at - start_at).total_seconds() / 3600)
        if not durations:
            return 0.0
        return round(sum(durations) / len(durations), 2)
