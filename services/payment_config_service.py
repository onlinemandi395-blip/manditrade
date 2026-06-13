from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from services.id_service import IdService
from services.notification_service import NotificationService
from services.payment_service import PaymentService


class PaymentConfigService:
    PENDING_PAYMENT_STATUSES = {"PENDING", "PAYMENT_PENDING"}

    def __init__(self, data_service, cache_service, admin_drive_service) -> None:
        self.data_service = data_service
        self.cache_service = cache_service
        self.admin_drive_service = admin_drive_service
        self.payment_service = PaymentService(data_service, cache_service)
        self.notification_service = NotificationService(data_service)
        self.id_service = IdService()

    def _normalize_payload(self, *, enabled: bool, currency: str, upi_id: str, payee_name: str) -> dict:
        return {
            "schema_version": 1,
            "payment": {
                "upi_id": str(upi_id or "").strip(),
                "payee_name": str(payee_name or "").strip() or "MandiTrade",
                "currency": str(currency or "INR").strip() or "INR",
                "enabled": bool(enabled),
            },
        }

    def _append_audit_log(
        self,
        *,
        actor_email: str,
        source_screen: str,
        previous_config: dict,
        next_config: dict,
        impact: dict,
    ) -> dict:
        record = {
            "audit_id": self.id_service.next("audit_log"),
            "event_type": "PAYMENT_RECEIVER_UPDATED",
            "title": "Merchant payment receiver updated",
            "source_entity": "payment_config",
            "source_id": "00_config/payment_config.json",
            "actor_email": str(actor_email or "").strip().lower(),
            "source_screen": str(source_screen or "").strip(),
            "created_at": datetime.now(UTC).isoformat(),
            "before": deepcopy(previous_config),
            "after": deepcopy(next_config),
            "impact": deepcopy(impact),
        }
        self.data_service.get_collection_ref("audit_logs").append(record)
        return record

    def _refresh_live_pending_queue(self) -> dict:
        now = datetime.now(UTC).isoformat()
        payment_config = self.payment_service.get_payment_config()
        payments_enabled = bool(payment_config.get("enabled", False))
        payments = self.data_service.get_collection_ref("payments")
        marketplace_orders = self.data_service.get_collection_ref("marketplace_orders")
        manditrade_orders = self.data_service.get_collection_ref("manditrade_orders")

        pending_payment_map: dict[str, dict] = {}
        updated_payments = 0

        for payment in payments:
            payment_status = str(payment.get("payment_status", payment.get("status", ""))).strip().upper()
            if payment_status not in self.PENDING_PAYMENT_STATUSES:
                continue
            reference = str(payment.get("payment_reference", "")).strip()
            if not reference:
                continue
            amount = float(payment.get("amount_payable", payment.get("amount_due", 0)) or 0)
            upi_link = self.payment_service.build_upi_link(amount=amount, reference=reference) if payments_enabled else ""
            payment["upi_link"] = upi_link
            payment["qr_payload"] = upi_link
            payment["receiver_upi_id"] = payment_config.get("upi_id", "")
            payment["receiver_payee_name"] = payment_config.get("payee_name", "")
            payment["receiver_currency"] = payment_config.get("currency", "INR")
            payment["payment_enabled"] = payments_enabled
            payment["receiver_updated_at"] = now
            pending_payment_map[str(payment.get("order_id", "")).strip()] = {
                "upi_link": upi_link,
                "qr_payload": upi_link,
                "payment_enabled": payments_enabled,
                "receiver_updated_at": now,
            }
            updated_payments += 1

        updated_marketplace_orders = 0
        updated_manditrade_orders = 0
        for order in marketplace_orders:
            order_status = str(order.get("payment_status", order.get("status", ""))).strip().upper()
            order_id = str(order.get("order_id", "")).strip()
            if order_status not in self.PENDING_PAYMENT_STATUSES or order_id not in pending_payment_map:
                continue
            order.update(pending_payment_map[order_id])
            order["updated_at"] = now
            updated_marketplace_orders += 1

        for order in manditrade_orders:
            order_status = str(order.get("payment_status", order.get("status", ""))).strip().upper()
            order_id = str(order.get("order_id", "")).strip()
            if order_status not in self.PENDING_PAYMENT_STATUSES or order_id not in pending_payment_map:
                continue
            order.update(pending_payment_map[order_id])
            order["updated_at"] = now
            updated_manditrade_orders += 1

        if updated_payments:
            self.data_service.persist_collection("payments")
        if updated_marketplace_orders:
            self.data_service.persist_collection("marketplace_orders")
        if updated_manditrade_orders:
            self.data_service.persist_collection("manditrade_orders")

        return {
            "pending_payments_updated": updated_payments,
            "marketplace_orders_updated": updated_marketplace_orders,
            "manditrade_orders_updated": updated_manditrade_orders,
            "pending_orders_updated": updated_marketplace_orders + updated_manditrade_orders,
        }

    def save_payment_receiver_settings(
        self,
        *,
        enabled: bool,
        currency: str,
        upi_id: str,
        payee_name: str,
        changed_by: str,
        source_screen: str,
    ) -> dict:
        if enabled and not str(upi_id).strip():
            raise ValueError("Merchant UPI ID is required when UPI payments are enabled.")

        previous_config = self.payment_service.get_payment_config()
        payload = self._normalize_payload(
            enabled=enabled,
            currency=currency,
            upi_id=upi_id,
            payee_name=payee_name,
        )
        next_config = dict(payload.get("payment", {}) or {})
        changed = any(
            str(previous_config.get(field, "")) != str(next_config.get(field, ""))
            for field in ("upi_id", "payee_name", "currency", "enabled")
        )

        self.admin_drive_service.write_json("00_config/payment_config.json", payload)
        self.cache_service.update_config("payment_config", payload)

        impact = {
            "pending_payments_updated": 0,
            "marketplace_orders_updated": 0,
            "manditrade_orders_updated": 0,
            "pending_orders_updated": 0,
        }
        audit_record = {}

        if changed:
            impact = self._refresh_live_pending_queue()
            audit_record = self._append_audit_log(
                actor_email=changed_by,
                source_screen=source_screen,
                previous_config=previous_config,
                next_config=next_config,
                impact=impact,
            )
            self.notification_service.create_notification(
                to_email="",
                title="Merchant payment receiver updated",
                message=(
                    "Merchant payment receiver settings were changed. "
                    f"Pending payments updated: {impact['pending_payments_updated']}, "
                    f"pending orders updated: {impact['pending_orders_updated']}."
                ),
                event_type="PAYMENT_RECEIVER_UPDATED",
                to_role="platform_admin",
                source_entity="payment_config",
                source_id="00_config/payment_config.json",
                metadata={
                    "source_screen": source_screen,
                    "previous_upi_id": previous_config.get("upi_id", ""),
                    "next_upi_id": next_config.get("upi_id", ""),
                    **impact,
                },
                created_by=changed_by,
            )
            self.data_service.persist_collection("audit_logs")
            self.data_service.persist_collection("notifications")
            self.data_service.persist_collection("gmail_queue")

        return {
            "changed": changed,
            "payment_config": next_config,
            "previous_config": previous_config,
            "impact": impact,
            "audit_record": audit_record,
        }
