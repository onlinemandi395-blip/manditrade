from __future__ import annotations

from components.html_renderer import render_html


def render_section_intro(title: str, description: str) -> None:
    render_html(
        f"""
        <div class="mt-section-intro">
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        """
    )
