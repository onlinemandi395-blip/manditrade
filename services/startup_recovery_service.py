from __future__ import annotations


class StartupRecoveryService:
    def __init__(
        self,
        procurement_transaction_service,
        order_transaction_service,
        file_lock_service,
        recovery_root=None,
        runtime_metrics_service=None,
    ) -> None:
        self.procurement_transaction_service = procurement_transaction_service
        self.order_transaction_service = order_transaction_service
        self.file_lock_service = file_lock_service
        self.recovery_root = recovery_root
        self.runtime_metrics_service = runtime_metrics_service

    def run_recovery_pass(self) -> dict:
        stale_locks = self.file_lock_service.cleanup_stale_locks()
        procurement = self.procurement_transaction_service.recover_incomplete_transactions()
        orders = self.order_transaction_service.recover_incomplete_transactions()
        payload = {
            "stale_locks_cleared": stale_locks,
            "procurement_recovered": procurement,
            "order_recovered": orders,
        }
        if self.runtime_metrics_service:
            self.runtime_metrics_service.increment(
                "recovery_runs",
                extra={
                    "stale_locks": len(stale_locks),
                    "procurement_recovered": len(procurement),
                    "order_recovered": len(orders),
                },
            )
        if self.recovery_root:
            from datetime import UTC, datetime
            import json
            self.recovery_root.mkdir(parents=True, exist_ok=True)
            target = self.recovery_root / f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}.json"
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
