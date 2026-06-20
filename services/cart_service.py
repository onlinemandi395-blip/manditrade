from __future__ import annotations

import streamlit as st

from services.pricing_service import PricingService


class CartService:
    def __init__(self, cart_key: str = "mt_next_cart") -> None:
        self.cart_key = str(cart_key or "mt_next_cart").strip() or "mt_next_cart"
        st.session_state.setdefault(self.cart_key, {"items": []})
        self.pricing_service = PricingService()

    def _normalize_items(self) -> list[dict]:
        raw_items = list((st.session_state.get(self.cart_key, {}) or {}).get("items", []) or [])
        merged_items: list[dict] = []
        merged_index: dict[str, dict] = {}
        anonymous_counter = 0
        for item in raw_items:
            product_id = str(item.get("product_id", "")).strip()
            channel = str(item.get("channel", "marketplace") or "marketplace").strip().lower() or "marketplace"
            if not product_id:
                anonymous_counter += 1
                product_id = f"cart-item-{anonymous_counter}"
            item_key = f"{channel}::{product_id}"
            quantity = max(1.0, float(item.get("quantity", item.get("qty", 1)) or 1))
            unit_price = float(item.get("unit_price", item.get("price", 0)) or 0)
            product_name = str(item.get("product_name", "") or "").strip()
            existing = merged_index.get(item_key)
            if existing:
                existing["quantity"] += quantity
                existing["line_total"] = round(float(existing.get("unit_price", 0) or 0) * float(existing.get("quantity", 1) or 1), 2)
                continue
            normalized = {
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "channel": channel,
                "unit_price": unit_price,
                "line_total": round(unit_price * quantity, 2),
                "cart_item_key": str(item.get("cart_item_key", "")).strip() or item_key,
                "product_code": str(item.get("product_code", "") or "").strip(),
                "category": str(item.get("category", "") or "").strip(),
                "subcategory": str(item.get("subcategory", "") or "").strip(),
                "unit": str(item.get("unit", "") or "").strip(),
                "owner_name": str(item.get("owner_name", "") or "").strip(),
            }
            merged_items.append(normalized)
            merged_index[item_key] = normalized
        st.session_state[self.cart_key] = {"items": merged_items}
        return merged_items

    def add_to_cart(self, product: dict, *, channel: str = "marketplace", quantity: float = 1.0) -> None:
        self._normalize_items()
        normalized_channel = str(channel or "marketplace").strip().lower() or "marketplace"
        sell_price = self.pricing_service.resolve_sell_price(product, normalized_channel)
        product_id = str(product.get("product_id", "")).strip()
        existing = next(
            (
                item
                for item in st.session_state[self.cart_key]["items"]
                if str(item.get("product_id", "")).strip() == product_id
                and str(item.get("channel", "marketplace") or "marketplace").strip().lower() == normalized_channel
            ),
            None,
        )
        if existing:
            next_quantity = max(1.0, float(existing.get("quantity", 1) or 1) + float(quantity or 1))
            existing["quantity"] = next_quantity
            existing["unit_price"] = sell_price
            existing["line_total"] = round(float(sell_price or 0) * next_quantity, 2)
            return
        item = {
            "product_id": product_id,
            "product_name": product.get("product_name", ""),
            "quantity": max(1.0, float(quantity or 1)),
            "channel": normalized_channel,
            "unit_price": sell_price,
            "line_total": round(float(sell_price or 0) * max(1.0, float(quantity or 1)), 2),
            "cart_item_key": f"{normalized_channel}::{product_id}" if product_id else f"cart-item-{len(st.session_state[self.cart_key]['items']) + 1}",
            "product_code": str(product.get("product_code", product_id) or "").strip(),
            "category": str(product.get("category", "") or "").strip(),
            "subcategory": str(product.get("subcategory", "") or "").strip(),
            "unit": str(product.get("unit", "") or "").strip(),
            "owner_name": str(((product.get("owner") or {}).get("display_name", "")) or "").strip(),
        }
        st.session_state[self.cart_key]["items"].append(item)

    def set_quantity(self, product_id: str, quantity: float, *, channel: str | None = None) -> None:
        self._normalize_items()
        normalized_id = str(product_id or "").strip()
        normalized_channel = str(channel or "").strip().lower()
        for item in st.session_state[self.cart_key]["items"]:
            if str(item.get("product_id", "")).strip() != normalized_id:
                continue
            if normalized_channel and str(item.get("channel", "")).strip().lower() != normalized_channel:
                continue
            normalized_quantity = max(1.0, float(quantity or 1))
            item["quantity"] = normalized_quantity
            item["line_total"] = round(float(item.get("unit_price", 0) or 0) * normalized_quantity, 2)
            return

    def remove_item(self, product_id: str, *, channel: str | None = None) -> None:
        self._normalize_items()
        normalized_channel = str(channel or "").strip().lower()
        st.session_state[self.cart_key]["items"] = [
            item
            for item in st.session_state[self.cart_key]["items"]
            if not (
                str(item.get("product_id", "")).strip() == str(product_id or "").strip()
                and (not normalized_channel or str(item.get("channel", "")).strip().lower() == normalized_channel)
            )
        ]

    def clear_cart(self) -> None:
        st.session_state[self.cart_key] = {"items": []}

    def get_cart(self) -> dict:
        return {"items": self._normalize_items()}

    def calculate_total(self) -> float:
        return round(
            sum(
                float(item.get("line_total", 0) or 0)
                if "line_total" in item
                else float(item.get("unit_price", 0) or 0) * int(item.get("quantity", item.get("qty", 0)) or 0)
                for item in self.get_cart()["items"]
            ),
            2,
        )
