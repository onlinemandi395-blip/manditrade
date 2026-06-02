from __future__ import annotations

from typing import Any


class TrustBadgeService:
    def badges_for_marketplace_order(self, order: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        if str(order.get("payment_status") or "").upper() == "VERIFIED":
            badges.append("Payment Verified")
        if str(order.get("status") or "").upper() in {"DISPATCHED", "DELIVERED"}:
            badges.append("Fast Dispatch")
        if self._average_rating(order) >= 4:
            badges.append("Top Rated Product")
        return badges

    def badges_for_supply_order(self, order: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        if str(order.get("status") or "").upper() in {"MAHAJAN_DISPATCHED", "MANUFACTURER_RECEIVED", "CLOSED"}:
            badges.append("Reliable Mahajan")
        if str(order.get("payment_verified_at") or "").strip():
            badges.append("Payment Verified")
        if self._average_rating(order) >= 4:
            badges.append("Trusted Supply Partner")
        return badges

    def admin_summary(self, *, products: list[dict[str, Any]], supply_orders: list[dict[str, Any]]) -> dict[str, list[str]]:
        low_rated_suppliers = sorted(
            {
                str(item.get("mahajan_id") or "").strip()
                for item in supply_orders
                if str(item.get("mahajan_id") or "").strip() and 0 < self._average_rating(item) < 3
            }
        )
        high_rated_products = sorted(
            {
                str(item.get("product_id") or "").strip()
                for item in products
                if str(item.get("product_id") or "").strip() and self._average_rating(item) >= 4
            }
        )
        return {
            "low_rated_suppliers": low_rated_suppliers,
            "high_rated_products": high_rated_products,
        }

    def _average_rating(self, item: dict[str, Any]) -> float:
        ratings = item.get("ratings") or []
        values = [float(entry.get("rating", 0) or 0) for entry in ratings if float(entry.get("rating", 0) or 0) > 0]
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)
