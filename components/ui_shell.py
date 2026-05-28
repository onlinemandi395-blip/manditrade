from __future__ import annotations

from html import escape
from pathlib import Path

from components.html_renderer import inject_css, render_html


def apply_ui_shell(css_path: Path) -> None:
    inject_css(css_path)


def render_page_header(title: str, subtitle: str, badges: list[str] | None = None) -> None:
    badge_html = "".join(f"<span class='mt-badge mt-badge-info'>{escape(badge)}</span>" for badge in (badges or []))
    render_html(
        f"""
        <section class="mt-hero">
          <div class="mt-hero__glow"></div>
          <div class="mt-hero__orb mt-hero__orb--warm"></div>
          <div class="mt-hero__orb mt-hero__orb--cool"></div>
          <div class="mt-hero__lane"></div>
          <div class="mt-hero__content">
            <p class="mt-kicker">3D Bharat Mandi Control Center</p>
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
            <div class="mt-badge-row">{badge_html}</div>
          </div>
        </section>
        """
    )


def render_metric_card(label: str, value: str, status: str = "SUCCESS") -> str:
    return f"""
    <article class="mt-card mt-card--metric">
      <div class="mt-card__label">{escape(label)}</div>
      <div class="mt-card__value">{escape(value)}</div>
      {render_status_badge(status)}
    </article>
    """


def render_action_card(title: str, description: str, button: str) -> str:
    return f"""
    <article class="mt-card mt-card--action">
      <h3>{escape(title)}</h3>
      <p>{escape(description)}</p>
      <div class="mt-button-chip">{escape(button)}</div>
    </article>
    """


def render_status_badge(status: str) -> str:
    css_class = f"mt-badge mt-badge-{status.lower().replace('_', '-')}"
    return f"<span class='{css_class}'>{escape(status)}</span>"


def render_3d_panel(content: str, title: str | None = None) -> None:
    title_html = f"<h3 class='mt-panel__title'>{escape(title)}</h3>" if title else ""
    render_html(f"<section class='mt-panel'>{title_html}<div class='mt-panel__body'>{content}</div></section>")


def render_showcase_strip(items: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        f"""
        <article class="mt-mini-stat">
          <div class="mt-mini-stat__meta">
            <span>{escape(label)}</span>
            {render_status_badge(status)}
          </div>
          <strong>{escape(value)}</strong>
        </article>
        """
        for label, value, status in items
    )
    render_html(f"<section class='mt-showcase-strip'>{cards}</section>")


def render_dual_panel(left_title: str, left_content: str, right_title: str, right_content: str) -> None:
    render_html(
        f"""
        <section class="mt-grid mt-grid--panels">
          <article class="mt-panel">
            <h3 class="mt-panel__title">{escape(left_title)}</h3>
            <div class="mt-panel__body">{left_content}</div>
          </article>
          <article class="mt-panel">
            <h3 class="mt-panel__title">{escape(right_title)}</h3>
            <div class="mt-panel__body">{right_content}</div>
          </article>
        </section>
        """
    )


def render_mobile_record_card(record: dict) -> str:
    rows = "".join(
        f"<div class='mt-record__row'><span>{escape(str(key))}</span><strong>{escape(str(value))}</strong></div>"
        for key, value in record.items()
    )
    return f"<article class='mt-record-card'>{rows}</article>"
