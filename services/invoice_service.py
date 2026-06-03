from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from utils.file_locking import atomic_write_text


class InvoiceService:
    def __init__(self, *, runtime_root: Path, safe_drive_write_service, id_allocator_service, json_service, event_notification_service=None) -> None:
        self.runtime_root = runtime_root
        self.safe_drive_write_service = safe_drive_write_service
        self.id_allocator_service = id_allocator_service
        self.json_service = json_service
        self.event_notification_service = event_notification_service
        self.invoices_root = runtime_root / "financial" / "invoices"

    def generate_invoice(
        self,
        *,
        invoice_type: str,
        related_order_id: str,
        bill_from: dict[str, Any],
        bill_to: dict[str, Any],
        items: list[dict[str, Any]],
        subtotal: float,
        tax_amount: float = 0,
        courier_amount: float = 0,
        packaging_amount: float = 0,
        commission_amount: float = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        invoice_id = self.id_allocator_service.allocate("invoice")
        payload = {
            "invoice_id": invoice_id,
            "invoice_type": str(invoice_type or "").strip().upper(),
            "related_order_id": str(related_order_id or "").strip(),
            "bill_from": bill_from,
            "bill_to": bill_to,
            "items": items,
            "subtotal": round(float(subtotal or 0), 2),
            "tax_amount": round(float(tax_amount or 0), 2),
            "courier_amount": round(float(courier_amount or 0), 2),
            "packaging_amount": round(float(packaging_amount or 0), 2),
            "commission_amount": round(float(commission_amount or 0), 2),
            "grand_total": round(float(subtotal or 0) + float(tax_amount or 0) + float(courier_amount or 0) + float(packaging_amount or 0) + float(commission_amount or 0), 2),
            "invoice_status": "GENERATED",
            "generated_at": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }
        self.invoices_root.mkdir(parents=True, exist_ok=True)
        self.safe_drive_write_service.replace_document(self.invoices_root / f"{invoice_id}.json", payload)
        atomic_write_text(self.invoices_root / f"{invoice_id}.html", self.render_invoice_html(payload), encoding="utf-8")
        if self.event_notification_service:
            self.event_notification_service.emit(
                "INVOICE_GENERATED",
                {
                    "entity_type": "INVOICE",
                    "entity_id": invoice_id,
                    "title": "Invoice generated",
                    "message": f"Invoice generated for {related_order_id}.",
                },
            )
        return payload

    def list_invoices(self) -> list[dict[str, Any]]:
        if not self.invoices_root.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.invoices_root.glob("*.json")):
            rows.append(self.json_service.read_json(path, {}))
        rows.sort(key=lambda item: item.get("generated_at", ""), reverse=True)
        return rows

    def render_invoice_html(self, invoice: dict[str, Any]) -> str:
        lines = [
            "<html><body>",
            f"<h1>{invoice.get('invoice_type', 'Invoice')}</h1>",
            f"<p>Invoice ID: {invoice.get('invoice_id', '')}</p>",
            f"<p>Order ID: {invoice.get('related_order_id', '')}</p>",
            "<ul>",
        ]
        for item in invoice.get("items", []):
            lines.append(
                f"<li>{item.get('name', '')} - {item.get('qty', 0)} {item.get('unit', '')} @ {item.get('unit_price', 0)}</li>"
            )
        lines.extend(
            [
                "</ul>",
                f"<p>Subtotal: {invoice.get('subtotal', 0)}</p>",
                f"<p>Tax: {invoice.get('tax_amount', 0)}</p>",
                f"<p>Packaging: {invoice.get('packaging_amount', 0)}</p>",
                f"<p>Courier: {invoice.get('courier_amount', 0)}</p>",
                f"<p>Commission: {invoice.get('commission_amount', 0)}</p>",
                f"<h2>Grand Total: {invoice.get('grand_total', 0)}</h2>",
                "</body></html>",
            ]
        )
        return "\n".join(lines)
