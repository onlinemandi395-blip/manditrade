from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RecommendationService:
    def __init__(self, *, recommendations_path: Path, safe_drive_write_service) -> None:
        self.recommendations_path = recommendations_path
        self.safe_drive_write_service = safe_drive_write_service

    def generate(self, app_context: dict) -> dict[str, list[dict[str, Any]]]:
        recommendations = {
            "platform_admin": self._for_admin(app_context),
            "manufacturer": self._for_manufacturers(app_context),
            "mahajan": self._for_mahajans(app_context),
        }
        payload = {"generated_at": datetime.now(UTC).isoformat(), "recommendations": recommendations}
        self.safe_drive_write_service.replace_document(self.recommendations_path, payload)
        return recommendations

    def read_latest(self) -> dict[str, Any]:
        if not self.recommendations_path.exists():
            return {}
        return __import__("json").loads(self.recommendations_path.read_text(encoding="utf-8"))

    def _for_admin(self, app_context: dict) -> list[dict[str, Any]]:
        alerts = app_context["alert_engine"].list_alerts(resolved=False)
        items: list[dict[str, Any]] = []
        if any(item.get("type") == "PENDING_APPROVAL_TOO_LONG" for item in alerts):
            items.append({"severity": "HIGH", "message": "Review product proposals that have been pending too long.", "route": "Product Approvals"})
        if any(item.get("type") == "OVERDUE_PAYMENT" for item in alerts):
            items.append({"severity": "HIGH", "message": "Follow up on overdue ledger entries before they grow further.", "route": "Payments"})
        if any(item.get("type") == "STALLED_MANDI_ORDER" for item in alerts):
            items.append({"severity": "HIGH", "message": "Unblock stalled mandi orders in the supply workflow.", "route": "Mandi Orders"})
        if not items:
            items.append({"severity": "LOW", "message": "Operations are stable. Review the Operations Center for routine monitoring.", "route": "Operations Center"})
        return items

    def _for_manufacturers(self, app_context: dict) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for manufacturer in app_context["governance_service"].list_manufacturers():
            manufacturer_code = manufacturer.get("manufacturer_code", "")
            inventory = app_context["inventory_query_service"].list_inventory_snapshot(manufacturer_code)
            if any(int(item.get("self_inventory", {}).get("available_qty", 0) or 0) <= 5 for item in inventory.get("items", [])):
                items.append({"manufacturer_code": manufacturer_code, "severity": "MEDIUM", "message": "Low self inventory detected. Reorder or replenish stock.", "route": "Inventory"})
            if any(str(item.get("status", "")).upper() == "OVERDUE" for item in app_context["ledger_service"].list_ledger_entries(manufacturer_code)):
                items.append({"manufacturer_code": manufacturer_code, "severity": "HIGH", "message": "Overdue ledger items need payment follow-up.", "route": "Ledger"})
        return items

    def _for_mahajans(self, app_context: dict) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for mahajan in app_context["governance_service"].list_mahajans():
            mahajan_id = mahajan.get("mahajan_id", "")
            orders = app_context["procurement_transaction_service"].list_supply_orders(mahajan_id=mahajan_id)
            if any(str(item.get("status", "")).upper() == "SENT_TO_MAHAJAN" for item in orders):
                items.append({"mahajan_id": mahajan_id, "severity": "MEDIUM", "message": "Pending quote requests are waiting for response.", "route": "Mandi Orders"})
            if any(str(item.get("status", "")).upper() == "MANUFACTURER_CONFIRMED" for item in orders):
                items.append({"mahajan_id": mahajan_id, "severity": "HIGH", "message": "Confirmed supply orders should move to dispatch quickly.", "route": "Mandi Orders"})
        return items
