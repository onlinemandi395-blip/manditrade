from __future__ import annotations

from html import escape

from components.html_renderer import render_html
from components.order_detail_view import render_order_detail_view
from components.ui_shell import render_3d_panel


def render_detail_drawer(detail_payload: dict, *, title: str = "Detail Drawer", tone: str = "subtle") -> None:
    render_3d_panel("", title, tone=tone)
    render_order_detail_view(detail_payload)


def render_catalog_detail_drawer(
    *,
    title: str,
    subtitle: str,
    image: dict[str, str],
    price_label: str,
    price_value: str,
    availability_label: str,
    metadata: dict[str, str] | None = None,
    badges: list[str] | None = None,
    description: str = "",
) -> None:
    render_3d_panel("", title, tone="subtle")
    metadata = metadata or {}
    badge_html = "".join(f"<span class='mt-chip'>{escape(item)}</span>" for item in (badges or [])[:4])
    metadata_html = "".join(
        f"<span class='mt-chip'>{escape(key)}: {escape(value)}</span>"
        for key, value in metadata.items()
        if str(value or "").strip()
    )
    render_html(
        f"""
        <article class="mt-product-card">
          <div class="mt-product-thumbnail" style="background-image:url('{escape(image['src'])}');" role="img" aria-label="{escape(image['alt'])}"></div>
          <div class="mt-chip-row">
            <span class="mt-chip">{escape(subtitle)}</span>
            <span class="mt-availability-chip">{escape(availability_label)}</span>
          </div>
          <div class="mt-chip-row">
            <span class="mt-price-chip">{escape(price_label)}: {escape(price_value)}</span>
            {metadata_html}
          </div>
          <p>{escape(description or "No additional description available.")}</p>
          <div class="mt-chip-row">{badge_html}</div>
        </article>
        """
    )
