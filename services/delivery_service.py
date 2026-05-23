from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from services.json_service import JsonService


class DeliveryService:
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

    def __init__(self, gmail_service, audit_service, id_allocator_service=None) -> None:
        self.gmail_service = gmail_service
        self.audit_service = audit_service
        self.json_service = JsonService()
        self.id_allocator_service = id_allocator_service

    def build_dispatch_record(
        self,
        order_id: str,
        vehicle_number: str,
        driver_name: str,
        transporter_name: str,
    ) -> dict[str, Any]:
        dispatch_id = self.id_allocator_service.allocate("dispatch") if self.id_allocator_service else f"DSP-{uuid4().hex[:8].upper()}"
        return {
            "dispatch_id": dispatch_id,
            "order_id": order_id,
            "status": "DISPATCHED",
            "dispatch_time": datetime.now(UTC).isoformat(),
            "vehicle_number": vehicle_number,
            "driver_name": driver_name,
            "transporter_name": transporter_name,
            "proof_images": [],
        }

    def save_delivery_proof(self, proofs_dir: Path, order_id: str, uploaded_file) -> str:
        extension = Path(uploaded_file.name).suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError("Only JPG, PNG, and PDF proofs are allowed.")
        proofs_dir.mkdir(parents=True, exist_ok=True)
        target = proofs_dir / f"{order_id}_{uuid4().hex[:6]}{extension}"
        target.write_bytes(uploaded_file.getbuffer())
        return str(target)

    def confirm_delivery(self, order: dict[str, Any], actor: str, comments: str = "", proof_path: str | None = None) -> dict[str, Any]:
        order["delivery_confirmation"] = {
            "actor": actor,
            "comments": comments,
            "proof_path": proof_path or "",
            "confirmed_at": datetime.now(UTC).isoformat(),
        }
        self.audit_service.log_event(
            "delivery_confirmed",
            actor=actor,
            details={"order_id": order.get("order_id", ""), "proof_path": proof_path or ""},
        )
        if order.get("client_email"):
            self.gmail_service.enqueue_message(
                to_email=order["client_email"],
                subject="Delivery Confirmed",
                body=f"Order {order.get('order_id', '')} delivery has been confirmed.",
                notification_type="delivery_confirmation",
            )
        return order
