from __future__ import annotations

from typing import Any


class ProcurementMatchingService:
    def rank_suppliers(self, request: dict[str, Any], supplier_inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
        product_id = request.get("product_id")
        city = request.get("city", "").lower()
        ranked = []
        for item in supplier_inventory:
            if item.get("product_code") != product_id:
                continue
            score = int(item.get("quantity", 0) - item.get("reserved_quantity", 0))
            if item.get("city", "").lower() == city:
                score += 50
            ranked.append({**item, "match_score": score})
        return sorted(ranked, key=lambda row: row.get("match_score", 0), reverse=True)
