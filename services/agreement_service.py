from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import UTC, datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class AgreementService:
    def __init__(self, id_allocator_service=None) -> None:
        self.id_allocator_service = id_allocator_service

    def _next_agreement_id(self) -> str:
        if self.id_allocator_service is not None:
            return self.id_allocator_service.allocate("agreement")
        from uuid import uuid4
        return f"AGR-{uuid4().hex[:10].upper()}"

    def create_procurement_agreement(
        self,
        buyer_manufacturer_id: str,
        seller_manufacturer_id: str,
        product_code: str,
        quantity: int,
        unit_price: float,
    ) -> dict[str, object]:
        agreement_id = self._next_agreement_id()
        return {
            "agreement_id": agreement_id,
            "type": "procurement",
            "status": "DRAFT",
            "buyer_manufacturer_id": buyer_manufacturer_id,
            "seller_manufacturer_id": seller_manufacturer_id,
            "product_code": product_code,
            "quantity": quantity,
            "unit_price": unit_price,
            "advance_required_ratio": 0.5,
            "created_at": datetime.now(UTC).isoformat(),
        }

    def create_order_agreement(
        self,
        order_id: str,
        manufacturer_id: str,
        client_id: str,
        items: list[dict[str, Any]],
        total_amount: float,
    ) -> dict[str, Any]:
        agreement_id = self._next_agreement_id()
        return {
            "agreement_id": agreement_id,
            "type": "order",
            "status": "DRAFT",
            "order_id": order_id,
            "manufacturer_id": manufacturer_id,
            "client_id": client_id,
            "items": items,
            "total_amount": total_amount,
            "advance_required_ratio": 0.5,
            "advance_amount": round(total_amount * 0.5, 2),
            "advance_status": "PENDING",
            "created_at": datetime.now(UTC).isoformat(),
        }

    def update_status(self, agreement: dict[str, Any], status: str) -> dict[str, Any]:
        agreement["status"] = status
        agreement["updated_at"] = datetime.now(UTC).isoformat()
        return agreement

    def confirm_advance(self, agreement: dict[str, Any], amount: float) -> dict[str, Any]:
        minimum = round(float(agreement.get("advance_amount", 0)), 2)
        agreement["advance_received"] = round(amount, 2)
        agreement["advance_status"] = "CONFIRMED" if amount >= minimum else "PENDING"
        agreement["status"] = "CONFIRMED" if amount >= minimum else "ADVANCE_PENDING"
        agreement["updated_at"] = datetime.now(UTC).isoformat()
        return agreement

    def generate_pdf(self, agreement: dict[str, Any], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(output_path), pagesize=A4)
        pdf.setTitle(str(agreement.get("agreement_id", "MandiTrade Agreement")))
        text = pdf.beginText(40, 800)
        text.setFont("Helvetica", 11)
        lines = [
            "MandiTrade Agreement",
            f"Agreement ID: {agreement.get('agreement_id', '')}",
            f"Type: {agreement.get('type', '')}",
            f"Status: {agreement.get('status', '')}",
            f"Created At: {agreement.get('created_at', '')}",
            "",
        ]
        for key in ("manufacturer_id", "client_id", "buyer_manufacturer_id", "seller_manufacturer_id", "order_id"):
            if agreement.get(key):
                lines.append(f"{key}: {agreement[key]}")
        if agreement.get("items"):
            lines.append("")
            lines.append("Items:")
            for item in agreement["items"]:
                lines.append(
                    f"- {item.get('product_name', item.get('product_code', 'ITEM'))}: "
                    f"{item.get('qty', item.get('quantity', 0))} @ Rs {item.get('mrp', item.get('unit_price', 0))}"
                )
        if agreement.get("advance_amount") is not None:
            lines.append("")
            lines.append(f"Advance Required: Rs {agreement.get('advance_amount', 0)}")
            lines.append(f"Advance Status: {agreement.get('advance_status', 'PENDING')}")
        for line in lines:
            text.textLine(str(line))
        pdf.drawText(text)
        pdf.showPage()
        pdf.save()
        return output_path
