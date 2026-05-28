from __future__ import annotations

from components.html_renderer import render_html


def render_section_intro(title: str, description: str) -> None:
    render_html(
        f"""
        <div class="mt-section-intro">
          <p class="mt-section-intro__kicker">Workspace Focus</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        """
    )
