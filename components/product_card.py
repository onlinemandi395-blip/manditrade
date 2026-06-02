from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.html_renderer import render_html


CARD_VARIANTS = {"MARKETPLACE_PRODUCT", "MANDIPLACE_PRODUCT", "RAW_MATERIAL", "SUTA_MANDI"}


def render_product_card(
    *,
    item: dict[str, Any],
    variant: str,
    image: dict[str, str],
    title: str,
    subtitle: str,
    price_label: str,
    price_value: str,
    availability_label: str,
    visibility_label: str,
    action_label: str,
    action_key: str,
) -> bool:
    normalized_variant = variant if variant in CARD_VARIANTS else "MARKETPLACE_PRODUCT"
    render_html(
        f"""
        <article class="mt-product-card" data-variant="{escape(normalized_variant)}">
          <div class="mt-product-thumbnail" style="background-image:url('{escape(image['src'])}');" role="img" aria-label="{escape(image['alt'])}"></div>
          <div class="mt-chip-row">
            <span class="mt-chip">{escape(subtitle)}</span>
            <span class="mt-availability-chip">{escape(availability_label)}</span>
            <span class="mt-chip">{escape(visibility_label)}</span>
          </div>
          <h3>{escape(title)}</h3>
          <div class="mt-chip-row">
            <span class="mt-price-chip">{escape(price_label)}: {escape(price_value)}</span>
            <span class="mt-chip">{escape(str(item.get('unit', 'unit')))}</span>
          </div>
        </article>
        """
    )
    return st.button(action_label, key=action_key, use_container_width=True)
