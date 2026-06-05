from __future__ import annotations

from typing import Any

from components.product_card import render_product_card


def render_raw_material_card(
    *,
    item: dict[str, Any],
    image: dict[str, str],
    title: str,
    subtitle: str,
    price_value: str,
    supplier_label: str,
    availability_label: str,
    action_label: str,
    action_key: str,
    badges: list[str] | None = None,
    supporting_text: str = "",
) -> bool:
    merged_badges = [supplier_label, *(badges or [])]
    return render_product_card(
        item=item,
        variant="RAW_MATERIAL",
        image=image,
        title=title,
        subtitle=subtitle,
        price_label="Supply",
        price_value=price_value,
        availability_label=availability_label,
        visibility_label="SOURCE",
        action_label=action_label,
        action_key=action_key,
        badges=merged_badges[:3],
        supporting_text=supporting_text,
    )
