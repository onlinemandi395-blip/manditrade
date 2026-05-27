from __future__ import annotations

from datetime import date
from typing import Any


class ActionCenterService:
    def __init__(self, governance_service, gmail_service, notification_center_service, ledger_service, order_query_service, procurement_query_service, dual_inventory_service) -> None:
        self.governance_service = governance_service
        self.gmail_service = gmail_service
        self.notification_center_service = notification_center_service
        self.ledger_service = ledger_service
        self.order_query_service = order_query_service
        self.procurement_query_service = procurement_query_service
        self.dual_inventory_service = dual_inventory_service

    def get_actions(self, user) -> list[dict[str, Any]]:
        if not user:
            return []
        role = user.role
        if role == "platform_admin":
            return self._admin_actions()
        if role in {"manufacturer", "admin_as_manufacturer"}:
            return self._manufacturer_actions(user.manufacturer_code or "")
        return self._client_actions(user.manufacturer_code or "", user.email)

    def _admin_actions(self) -> list[dict[str, Any]]:
        actions = []
        manufacturers = self.governance_service.list_manufacturers()
        products = self.governance_service.list_products()
        failed_gmail = [item for item in self.gmail_service.read_queue() if item.get("status") == "failed"]
        if any(item.get("status") != "approved" for item in manufacturers):
            actions.append({"type": "APPROVE_MANUFACTURER", "count": len([item for item in manufacturers if item.get("status") != "approved"])})
        if any(item.get("status") == "PENDING_APPROVAL" for item in products):
            actions.append({"type": "APPROVE_PRODUCT", "count": len([item for item in products if item.get("status") == "PENDING_APPROVAL"])})
        if failed_gmail:
            actions.append({"type": "FAILED_GMAIL_NOTIFICATIONS", "count": len(failed_gmail)})
        return actions

    def _manufacturer_actions(self, manufacturer_code: str) -> list[dict[str, Any]]:
        actions = []
        orders = self.order_query_service.list_orders(manufacturer_code)
        rfqs = self.procurement_query_service.list_procurement_requests(manufacturer_code)
        ledgers = self.ledger_service.list_ledgers(manufacturer_code)
        inventory = self.dual_inventory_service.list_inventory(manufacturer_code)
        if any(item.get("status") in {"PROPOSED", "COUNTER_PROPOSED", "READY_TO_CONFIRM"} for item in orders):
            actions.append({"type": "CONFIRM_CLIENT_ORDER", "count": len([item for item in orders if item.get("status") in {"PROPOSED", "COUNTER_PROPOSED", "READY_TO_CONFIRM"}])})
        if any(item.get("status") == "OPEN" for item in rfqs):
            actions.append({"type": "RESPOND_RFQ", "count": len([item for item in rfqs if item.get("status") == "OPEN"])})
        if any(item.get("status") == "BUYER_CONFIRMED" for item in rfqs):
            actions.append({"type": "DISPATCH_PENDING", "count": len([item for item in rfqs if item.get("status") == "BUYER_CONFIRMED"])})
        overdue = 0
        for ledger in ledgers:
            for entry in ledger.get("entries", []):
                if entry.get("status") == "PENDING" and entry.get("due_date", "9999-12-31") < date.today().isoformat():
                    overdue += 1
        if overdue:
            actions.append({"type": "PAYMENT_OVERDUE", "count": overdue})
        low_stock = sum(1 for item in inventory.get("items", []) if int(item.get("self_inventory", {}).get("available_qty", 0)) <= 10)
        if low_stock:
            actions.append({"type": "LOW_INVENTORY", "count": low_stock})
        return actions

    def _client_actions(self, manufacturer_code: str, client_email: str) -> list[dict[str, Any]]:
        orders = self.order_query_service.list_orders_for_client(manufacturer_code, client_email)
        actions = []
        if any(item.get("status") == "COUNTER_PROPOSED" for item in orders):
            actions.append({"type": "ACCEPT_COUNTER_PROPOSAL", "count": len([item for item in orders if item.get("status") == "COUNTER_PROPOSED"])})
        if any(item.get("status") == "DELIVERED" for item in orders):
            actions.append({"type": "CONFIRM_DELIVERY", "count": len([item for item in orders if item.get("status") == "DELIVERED"])})
        return actions
