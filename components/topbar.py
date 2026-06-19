from __future__ import annotations

from components.html_renderer import render_template


def render_topbar(app_name: str, version: str, role_label: str, language: str, translator) -> None:
    role_text = role_label or "Workspace"
    render_template(
        "topbar.html",
        app_name=app_name,
        version=version,
        role_text=role_text,
        language_label=translator.t("auth.language"),
        language=language.upper(),
    )
