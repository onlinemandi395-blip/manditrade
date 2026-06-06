from __future__ import annotations

import streamlit as st

from components.product_card import render_product_card
from components.empty_state import render_empty_state


def render_product_grid(products: list[dict], *, view: str = "marketplace", on_add_to_cart=None, on_request=None) -> None:
    if not products:
      render_empty_state("No products found.")
      return
    columns = st.columns(3)
    for index, product in enumerate(products):
        with columns[index % 3]:
            render_product_card(product, view=view, on_add_to_cart=on_add_to_cart if view == "marketplace" else on_request)
