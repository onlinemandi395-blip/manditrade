from __future__ import annotations

from typing import Any


class TrustBadgeService:
    def badges_for_marketplace_product(self, product: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        visibility = str(product.get("approved_visibility") or product.get("visibility_request") or "").upper()
        minimum_qty = int(product.get("minimum_order_qty", 1) or 1)
        if visibility == "PUBLIC":
            badges.append("Public Catalog")
        if bool(product.get("available_for_public_sale")):
            badges.append("Ready To Ship")
        if minimum_qty <= 2:
            badges.append("Low MOQ")
        if self._average_rating(product) >= 4:
            badges.append("Top Rated Product")
        seller_id = str(product.get("public_seller_manufacturer_id") or product.get("created_by_manufacturer_id") or "").strip()
        if seller_id:
            badges.extend(self.badges_for_manufacturer({"manufacturer_id": seller_id, **product}))
        return self._dedupe(badges)

    def badges_for_raw_material(self, material: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        available_qty = float(material.get("available_qty", 0) or 0)
        category = str(material.get("category") or "").upper()
        if available_qty > 0:
            badges.append("Available Now")
        if available_qty >= 50:
            badges.append("Bulk Ready")
        if category == "SUTA":
            badges.append("Yarn Specialist")
        if str(material.get("mahajan_id") or "").strip():
            badges.append("Trusted Mahajan")
        if self._average_rating(material) >= 4:
            badges.append("Quality Supplier")
        return self._dedupe(badges)

    def badges_for_manufacturer(self, manufacturer: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        if str(manufacturer.get("status") or "").upper() == "ACTIVE":
            badges.append("Verified Manufacturer")
        if bool(manufacturer.get("available_for_public_sale", False)):
            badges.append("Marketplace Seller")
        if self._average_rating(manufacturer) >= 4:
            badges.append("High Fulfillment")
        return self._dedupe(badges)

    def badges_for_supplier_summary(self, entity: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        status = str(entity.get("status") or "").upper()
        if status in {"ACTIVE", "APPROVED"}:
            badges.append("Verified Supplier")
        if self._average_rating(entity) >= 4:
            badges.append("Repeat Supplier")
        if str(entity.get("city") or "").strip():
            badges.append(f"Ships From {str(entity.get('city')).strip()}")
        return self._dedupe(badges)

    def badges_for_marketplace_order(self, order: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        if str(order.get("payment_status") or "").upper() == "VERIFIED":
            badges.append("Payment Verified")
        if str(order.get("status") or "").upper() in {"DISPATCHED", "DELIVERED"}:
            badges.append("Fast Dispatch")
        if self._average_rating(order) >= 4:
            badges.append("Top Rated Product")
        return self._dedupe(badges)

    def badges_for_supply_order(self, order: dict[str, Any]) -> list[str]:
        badges: list[str] = []
        if str(order.get("status") or "").upper() in {"MAHAJAN_DISPATCHED", "MANUFACTURER_RECEIVED", "CLOSED"}:
            badges.append("Reliable Mahajan")
        if str(order.get("payment_verified_at") or "").strip():
            badges.append("Payment Verified")
        if str(order.get("courier", {}).get("status") or "").upper() in {"BOOKED", "IN_TRANSIT", "DELIVERED"}:
            badges.append("Courier Tracked")
        if str(order.get("packaging", {}).get("packaging_service_id") or "").strip():
            badges.append("Packaging Assigned")
        if self._average_rating(order) >= 4:
            badges.append("Trusted Supply Partner")
        return self._dedupe(badges)

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

    def _dedupe(self, badges: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for badge in badges:
            normalized = str(badge or "").strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(normalized)
        return unique
