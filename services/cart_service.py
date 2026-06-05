from __future__ import annotations

import streamlit as st


class CartService:
    def __init__(self) -> None:
        st.session_state.setdefault("mt_next_cart", {"items": []})

    def add_to_cart(self, product: dict) -> None:
        item = {
            "product_id": product.get("product_id", ""),
            "product_name": product.get("product_name", ""),
            "qty": 1,
            "price": ((product.get("sales_channels") or {}).get("marketplace") or {}).get("price", 0),
        }
        st.session_state["mt_next_cart"]["items"].append(item)

    def remove_item(self, product_id: str) -> None:
        st.session_state["mt_next_cart"]["items"] = [item for item in st.session_state["mt_next_cart"]["items"] if item.get("product_id") != product_id]

    def clear_cart(self) -> None:
        st.session_state["mt_next_cart"] = {"items": []}

    def get_cart(self) -> dict:
        return st.session_state["mt_next_cart"]

    def calculate_total(self) -> float:
        return round(sum(float(item.get("price", 0) or 0) * int(item.get("qty", 0) or 0) for item in self.get_cart()["items"]), 2)
