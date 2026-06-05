from __future__ import annotations

from components.html_renderer import render_html
from components.status_chip import render_status_chip


def render_metric_card(title: str, value: str, subtitle: str = "") -> None:
    render_html(
        f"""
        <article class="mt-card">
          <h3>{title}</h3>
          <div class="mt-kpi-value">{value}</div>
          <p class="mt-muted">{subtitle}</p>
        </article>
        """
    )


def render_entity_card(title: str, body: str, status: str = "") -> None:
    status_html = render_status_chip(status) if status else ""
    render_html(
        f"""
        <article class="mt-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;">
            <h3>{title}</h3>
            {status_html}
          </div>
          <div class="mt-muted">{body}</div>
        </article>
        """
    )
