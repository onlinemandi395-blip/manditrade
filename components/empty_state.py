from __future__ import annotations

from html import escape

from components.html_renderer import render_html


def render_empty_state_block(message: str, *, icon: str = "[]", cta: str = "") -> None:
    cta_html = f"<div class='mt-action-chip'>{escape(cta)}</div>" if cta else ""
    render_html(
        f"""
        <section class="mt-empty-state">
          <div class="mt-empty-state__icon">{escape(icon)}</div>
          <strong>{escape(message)}</strong>
          {cta_html}
        </section>
        """
    )
