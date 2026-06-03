from __future__ import annotations

from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from utils.deep_links import build_deep_link_target


class OperationalSearchService:
    def __init__(self, *, index_path: Path | None = None, safe_drive_write_service=None) -> None:
        self.index_path = index_path
        self.safe_drive_write_service = safe_drive_write_service

    def search(self, app_context: dict, query: str) -> list[dict[str, Any]]:
        normalized = query.strip().lower()
        if not normalized:
            return []
        indexed = self._search_index(query)
        if indexed:
            results = indexed
        else:
            results = self._build_records(app_context, normalized)
        return self._rank_results(results, normalized)[:25]

    def _build_records(self, app_context: dict, normalized: str = "") -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        governance = app_context["governance_service"]
        for manufacturer in governance.list_manufacturers():
            if not normalized or normalized in str(manufacturer.get("manufacturer_code", "")).lower() or normalized in str(manufacturer.get("business_name", "")).lower():
                results.append({"label": manufacturer.get("business_name", manufacturer.get("manufacturer_code", "")), "entity_type": "manufacturer", "entity_id": manufacturer.get("manufacturer_code", ""), "target": {"route": "Manufacturers", "source_id": manufacturer.get("manufacturer_code", "")}})
        for mahajan in governance.list_mahajans():
            if not normalized or normalized in str(mahajan.get("mahajan_id", "")).lower() or normalized in str(mahajan.get("business_name", "")).lower():
                results.append({"label": mahajan.get("business_name", mahajan.get("mahajan_id", "")), "entity_type": "mahajan", "entity_id": mahajan.get("mahajan_id", ""), "target": {"route": "Mahajans", "source_id": mahajan.get("mahajan_id", "")}})
        for product in governance.list_products():
            if not normalized or normalized in str(product.get("product_id", "")).lower() or normalized in str(product.get("name", "")).lower():
                results.append({"label": product.get("name", product.get("product_id", "")), "entity_type": "product", "entity_id": product.get("product_id", ""), "target": build_deep_link_target("PRODUCT_PROPOSAL", product.get("product_id", ""))})
        for item in governance.list_raw_materials():
            if not normalized or normalized in str(item.get("raw_material_id", "")).lower() or normalized in str(item.get("name", "")).lower():
                results.append({"label": item.get("name", item.get("raw_material_id", "")), "entity_type": "raw_material", "entity_id": item.get("raw_material_id", ""), "target": {"route": "Raw Materials", "source_id": item.get("raw_material_id", "")}})
        for order in governance.list_supply_orders():
            if not normalized or normalized in str(order.get("mandi_order_id", "")).lower():
                results.append({"label": order.get("mandi_order_id", ""), "entity_type": "supply_order", "entity_id": order.get("mandi_order_id", ""), "target": build_deep_link_target("SUPPLY_ORDER", order.get("mandi_order_id", ""))})
        for order in app_context["public_order_service"].list_all_orders():
            if not normalized or normalized in str(order.get("public_order_id", "")).lower():
                results.append({"label": order.get("public_order_id", ""), "entity_type": "public_order", "entity_id": order.get("public_order_id", ""), "target": build_deep_link_target("PUBLIC_ORDER", order.get("public_order_id", ""))})
        settlement_service = app_context.get("settlement_service")
        if settlement_service:
            for transaction in settlement_service.list_transactions():
                if not normalized or normalized in str(transaction.get("financial_transaction_id", "")).lower():
                    results.append({"label": transaction.get("financial_transaction_id", ""), "entity_type": "financial_transaction", "entity_id": transaction.get("financial_transaction_id", ""), "target": {"route": "Finance Operations", "source_id": transaction.get("financial_transaction_id", "")}})
        invoice_service = app_context.get("invoice_service")
        if invoice_service:
            for invoice in invoice_service.list_invoices():
                if not normalized or normalized in str(invoice.get("invoice_id", "")).lower():
                    results.append({"label": invoice.get("invoice_id", ""), "entity_type": "invoice", "entity_id": invoice.get("invoice_id", ""), "target": {"route": "Finance Operations", "source_id": invoice.get("invoice_id", "")}})
        for dispute in governance.list_disputes():
            if not normalized or normalized in str(dispute.get("dispute_id", "")).lower():
                results.append({"label": dispute.get("dispute_id", ""), "entity_type": "dispute", "entity_id": dispute.get("dispute_id", ""), "target": {"route": "Finance Operations", "source_id": dispute.get("dispute_id", "")}})
        procurement_service = app_context.get("procurement_transaction_service")
        if procurement_service:
            for logistics in procurement_service.list_mandiplace_orders():
                if not normalized or normalized in str(logistics.get("mandiplace_order_id", "")).lower():
                    results.append({"label": logistics.get("mandiplace_order_id", ""), "entity_type": "logistics", "entity_id": logistics.get("mandiplace_order_id", ""), "target": {"route": "Logistics", "source_id": logistics.get("mandiplace_order_id", "")}})
        for manufacturer in governance.list_manufacturers():
            for entry in app_context["ledger_service"].list_ledger_entries(manufacturer.get("manufacturer_code", "")):
                if not normalized or normalized in str(entry.get("entry_id", "")).lower():
                    results.append({"label": entry.get("entry_id", ""), "entity_type": "ledger_entry", "entity_id": entry.get("entry_id", ""), "target": build_deep_link_target("LEDGER", entry.get("entry_id", ""))})
        return results

    def rebuild_index(self, app_context: dict) -> dict[str, Any]:
        rows = self._build_records(app_context)
        payload = {"generated_at": datetime.now(UTC).isoformat(), "records": rows}
        if self.index_path and self.safe_drive_write_service:
            self.safe_drive_write_service.replace_document(self.index_path, payload)
        return payload

    def _search_index(self, query: str) -> list[dict[str, Any]]:
        if not self.index_path or not self.index_path.exists():
            return []
        payload = __import__("json").loads(self.index_path.read_text(encoding="utf-8"))
        normalized = query.strip().lower()
        return [
            item for item in payload.get("records", [])
            if normalized in str(item.get("label", "")).lower()
            or normalized in str(item.get("entity_id", "")).lower()
            or normalized in str(item.get("entity_type", "")).lower()
        ][:25]

    def _rank_results(self, results: list[dict[str, Any]], normalized: str) -> list[dict[str, Any]]:
        def score(item: dict[str, Any]) -> float:
            haystacks = [
                str(item.get("label", "")).lower(),
                str(item.get("entity_id", "")).lower(),
                str(item.get("entity_type", "")).lower(),
            ]
            base = 0.0
            for value in haystacks:
                if value == normalized:
                    base = max(base, 100.0)
                elif normalized in value:
                    base = max(base, 70.0)
                else:
                    base = max(base, SequenceMatcher(None, normalized, value).ratio() * 50.0)
            return base

        return sorted(results, key=score, reverse=True)
