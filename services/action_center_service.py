from __future__ import annotations

from datetime import date
from typing import Any


class ActionCenterService:
    def __init__(self, governance_service, gmail_service, notification_center_service, ledger_service, order_query_service, procurement_query_service, dual_inventory_service, job_service=None, worker_service=None, public_order_service=None) -> None:
        self.governance_service = governance_service
        self.gmail_service = gmail_service
        self.notification_center_service = notification_center_service
        self.ledger_service = ledger_service
        self.order_query_service = order_query_service
        self.procurement_query_service = procurement_query_service
        self.dual_inventory_service = dual_inventory_service
        self.job_service = job_service
        self.worker_service = worker_service
        self.public_order_service = public_order_service

    def get_actions(self, user) -> list[dict[str, Any]]:
        if not user:
            return []
        role = user.role
        if role == "platform_admin":
            return self._admin_actions()
        if role == "mahajan":
            return self._mahajan_actions(user.email)
        if role in {"manufacturer", "admin_as_manufacturer"}:
            return self._manufacturer_actions(user.manufacturer_code or "")
        if role == "public_buyer":
            return self._public_buyer_actions(user.email)
        if role == "worker":
            return self._worker_actions(user.email)
        return []

    def _admin_actions(self) -> list[dict[str, Any]]:
        actions = []
        products = self.governance_service.list_products()
        supply_orders = self.governance_service.list_supply_orders() if hasattr(self.governance_service, "list_supply_orders") else []
        if any(item.get("status") == "PROPOSED" for item in products):
            actions.append({"type": "APPROVE_PRODUCT", "count": len([item for item in products if item.get("status") == "PROPOSED"])})
        unresolved = len([item for item in products if item.get("status") == "PROPOSED" and item.get("clarification_status") == "ADMIN_QUERY"])
        reply_pending = len([item for item in products if item.get("status") == "PROPOSED" and item.get("clarification_status") == "MANUFACTURER_REPLIED"])
        if unresolved:
            actions.append({"type": "PRODUCT_PROPOSAL_CLARIFICATION_UNRESOLVED", "count": unresolved})
        if reply_pending:
            actions.append({"type": "PRODUCT_PROPOSAL_REPLY_PENDING_REVIEW", "count": reply_pending})
        if self.public_order_service:
            public_orders = self.public_order_service.list_all_orders()
            failed_payments = len([item for item in public_orders if item.get("payment_status") == "FAILED"])
            if failed_payments:
                actions.append({"type": "REVIEW_FAILED_PUBLIC_PAYMENT", "count": failed_payments})
            if public_orders:
                actions.append({"type": "MONITOR_PUBLIC_ORDERS", "count": len(public_orders)})
            source_contact_needed = len(
                [
                    item
                    for item in public_orders
                    if item.get("status") in {"PAYMENT_PENDING", "PAID", "CONFIRMED"}
                    and any(
                        str(product.get("source_email") or product.get("source_mobile") or "").strip()
                        for product in item.get("items", [])
                    )
                ]
            )
            if source_contact_needed:
                actions.append({"type": "CONTACT_PRODUCT_SOURCE", "count": source_contact_needed})
        if supply_orders:
            manufacturer_requests = len([item for item in supply_orders if item.get("status") == "REQUESTED_BY_MANUFACTURER"])
            quoted = len([item for item in supply_orders if item.get("status") == "MAHAJAN_QUOTED"])
            if manufacturer_requests:
                actions.append({"type": "REVIEW_MANDI_REQUEST", "count": manufacturer_requests})
            if quoted:
                actions.append({"type": "SET_ADMIN_SUPPLY_PRICE", "count": quoted})
        return actions

    def _manufacturer_actions(self, manufacturer_code: str) -> list[dict[str, Any]]:
        actions = []
        products = self.governance_service.list_products()
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
        if self.job_service:
            pending_applications = len([item for item in self.job_service.list_applications(manufacturer_id=manufacturer_code) if item.get("status") == "APPLIED"])
            if pending_applications:
                actions.append({"type": "REVIEW_WORKER_APPLICATION", "count": pending_applications})
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
        product_reply_needed = len(
            [
                item
                for item in products
                if item.get("status") == "PROPOSED"
                and item.get("clarification_status") == "ADMIN_QUERY"
                and (item.get("created_by_manufacturer_id") == manufacturer_code or item.get("created_by") == manufacturer_code)
            ]
        )
        if product_reply_needed:
            actions.append({"type": "PRODUCT_PROPOSAL_NEEDS_REPLY", "count": product_reply_needed})
        if self.public_order_service:
            public_orders = self.public_order_service.list_orders_for_seller(manufacturer_code)
            payment_submitted = len([item for item in public_orders if item.get("payment_status") == "SUBMITTED"])
            paid = len([item for item in public_orders if item.get("status") == "PAID"])
            confirmed = len([item for item in public_orders if item.get("status") == "CONFIRMED"])
            if payment_submitted:
                actions.append({"type": "VERIFY_PUBLIC_PAYMENT", "count": payment_submitted})
            if paid:
                actions.append({"type": "CONFIRM_PUBLIC_ORDER", "count": paid})
            if confirmed:
                actions.append({"type": "DISPATCH_PUBLIC_ORDER", "count": confirmed})
        if hasattr(self.governance_service, "list_supply_orders"):
            supply_orders = [item for item in self.governance_service.list_supply_orders() if item.get("manufacturer_id") == manufacturer_code]
            awaiting_confirmation = len([item for item in supply_orders if item.get("status") == "ADMIN_PRICE_SET"])
            dispatched = len([item for item in supply_orders if item.get("status") == "MAHAJAN_DISPATCHED"])
            if awaiting_confirmation:
                actions.append({"type": "CONFIRM_ADMIN_SUPPLY_ORDER", "count": awaiting_confirmation})
            if dispatched:
                actions.append({"type": "RECEIVE_ADMIN_SUPPLY_ORDER", "count": dispatched})
        return actions

    def _mahajan_actions(self, email: str) -> list[dict[str, Any]]:
        actions = []
        if not hasattr(self.governance_service, "get_mahajan_by_email"):
            return actions
        mahajan = self.governance_service.get_mahajan_by_email(email)
        if not mahajan:
            return actions
        supply_orders = [item for item in self.governance_service.list_supply_orders() if item.get("mahajan_id") == mahajan.get("mahajan_id")]
        quote_needed = len([item for item in supply_orders if item.get("status") == "SENT_TO_MAHAJAN"])
        dispatch_needed = len([item for item in supply_orders if item.get("status") == "MANUFACTURER_CONFIRMED"])
        if quote_needed:
            actions.append({"type": "QUOTE_SUPPLY_ORDER", "count": quote_needed})
        if dispatch_needed:
            actions.append({"type": "DISPATCH_SUPPLY_ORDER", "count": dispatch_needed})
        return actions

    def _worker_actions(self, email: str) -> list[dict[str, Any]]:
        actions = []
        if not self.worker_service or not self.job_service:
            return actions
        worker = self.worker_service.get_worker_by_email(email)
        if not worker:
            return actions
        applications = self.job_service.list_applications(worker_id=worker["worker_id"])
        open_jobs = self.job_service.list_open_jobs() if worker.get("available") else []
        if open_jobs:
            actions.append({"type": "RESPOND_TO_JOB", "count": len(open_jobs)})
        confirmable = len([item for item in applications if item.get("status") == "ACCEPTED"])
        if confirmable:
            actions.append({"type": "CONFIRM_ATTENDANCE", "count": confirmable})
        return actions

    def _public_buyer_actions(self, email: str) -> list[dict[str, Any]]:
        actions = []
        if not self.public_order_service:
            return actions
        buyer = getattr(self.public_order_service.public_buyer_service, "get_by_email")(email)
        if not buyer:
            return actions
        orders = self.public_order_service.list_orders_for_buyer(buyer["public_buyer_id"])
        payment_pending = len([item for item in orders if item.get("status") == "PAYMENT_PENDING" and not item.get("payment_reference")])
        payment_reference_needed = len([item for item in orders if item.get("status") == "PAYMENT_PENDING" and item.get("payment_status") == "PENDING"])
        delivered = len([item for item in orders if item.get("status") == "DISPATCHED"])
        if payment_pending:
            actions.append({"type": "COMPLETE_PUBLIC_PAYMENT", "count": payment_pending})
        if payment_reference_needed:
            actions.append({"type": "UPLOAD_PAYMENT_REFERENCE", "count": payment_reference_needed})
        if delivered:
            actions.append({"type": "CONFIRM_PUBLIC_DELIVERY", "count": delivered})
        return actions
