from __future__ import annotations

from html import escape

import streamlit.components.v1 as components

from components.html_renderer import render_template


def render_frontend_shell(*, eyebrow: str, title: str, subtitle: str) -> None:
    render_template(
        "frontend_shell_open.html",
        eyebrow=eyebrow,
        title=title,
        subtitle=subtitle,
    )


def render_frontend_section(*, eyebrow: str, title: str, subtitle: str = "") -> None:
    render_template(
        "frontend_section_open.html",
        eyebrow=eyebrow,
        title=title,
        subtitle=subtitle,
    )


def render_frontend_cta_link(*, label: str, href: str, target: str = "_self") -> None:
    safe_label = escape(str(label or "Open"))
    safe_href = escape(str(href or ""))
    safe_target = escape(str(target or "_self"))
    components.html(
        f"""
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8" />
          <style>
            html, body {{
              margin: 0;
              padding: 0;
              background: transparent;
              font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            }}
            .mt-cta-link {{
              display: inline-flex;
              align-items: center;
              justify-content: center;
              width: 100%;
              min-height: 46px;
              padding: 0.72rem 1rem;
              box-sizing: border-box;
              border-radius: 14px;
              text-decoration: none;
              color: #ffffff;
              background: linear-gradient(135deg, #f20530, #d90429 60%, #7a0016);
              border: 1px solid transparent;
              font-weight: 700;
            }}
          </style>
        </head>
        <body>
          <a class="mt-cta-link" href="{safe_href}" target="{safe_target}" rel="noopener noreferrer">{safe_label}</a>
        </body>
        </html>
        """,
        height=58,
        scrolling=False,
    )
