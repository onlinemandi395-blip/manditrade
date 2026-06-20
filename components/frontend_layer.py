from __future__ import annotations

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


def render_frontend_cta_link(*, label: str, href: str) -> None:
    render_template(
        "frontend_cta_link.html",
        label=label,
        href=href,
    )
