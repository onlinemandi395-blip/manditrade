from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from components import command_palette, toast_manager
from services.operational_search_service import OperationalSearchService
from services.session_state_service import SessionStateService


def test_command_palette_mentions_keyboard_shortcut_and_recent_searches(monkeypatch):
    writes: list[str] = []
    fake_streamlit = SimpleNamespace(
        markdown=lambda *args, **kwargs: None,
        text_input=lambda *args, **kwargs: "",
        button=lambda *args, **kwargs: False,
        caption=lambda text: writes.append(text),
        write=lambda text: writes.append(str(text)),
        info=lambda text: writes.append(text),
        session_state={"show_command_palette": True},
    )
    app_context = {
        "operational_search_service": SimpleNamespace(search=lambda _ctx, _query: []),
        "session_state_service": SimpleNamespace(get_recent_searches=lambda: ["ORD-1"], add_recent_search=lambda _query: None),
        "available_routes": ["Dashboard", "Payments"],
    }
    monkeypatch.setattr("components.command_palette.st", fake_streamlit)
    monkeypatch.setattr("components.command_palette.render_html", lambda html, height=None: writes.append(html))

    command_palette.render_command_palette(app_context)

    assert any("Ctrl/Cmd + K" in item for item in writes)
    assert any("Recent searches" in item for item in writes)


def test_toast_manager_push_and_render(monkeypatch):
    html_calls: list[str] = []
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr("components.toast_manager.st", fake_streamlit)
    monkeypatch.setattr("components.toast_manager.render_html", lambda html, height=None: html_calls.append(html))

    toast_manager.push_toast("Product Created", tone="success", title="Saved")
    toast_manager.render_toasts()

    assert fake_streamlit.session_state["mt_toasts"]
    assert any("Product Created" in html for html in html_calls)


def test_session_state_tracks_recent_searches_and_unsaved_changes(monkeypatch):
    fake_streamlit = SimpleNamespace(session_state={})
    monkeypatch.setattr("services.session_state_service.st", fake_streamlit)

    service = SessionStateService()
    service.add_recent_search("ORD-1")
    service.mark_unsaved_changes("demo_form")

    assert service.get_recent_searches() == ["ORD-1"]
    assert service.has_unsaved_changes() is True
    assert service.list_unsaved_forms() == ["demo_form"]

    service.clear_unsaved_changes("demo_form")
    assert service.has_unsaved_changes() is False


def test_operational_search_supports_fuzzy_rank():
    service = OperationalSearchService()
    ranked = service._rank_results(
        [
            {"label": "Manufacturer Alpha", "entity_id": "MANU101", "entity_type": "manufacturer"},
            {"label": "Invoice 2026", "entity_id": "INV-1", "entity_type": "invoice"},
        ],
        "manu",
    )

    assert ranked[0]["entity_type"] == "manufacturer"


def test_production_experience_docs_and_reliability_section_exist():
    docs = Path("docs/PRODUCTION_EXPERIENCE.md").read_text(encoding="utf-8")
    health = Path("modules/system/health_dashboard.py").read_text(encoding="utf-8")
    bootstrap = Path("bootstrap/app_bootstrap.py").read_text(encoding="utf-8")

    assert "Command Palette" in docs
    assert "Toast Model" in docs
    assert "Operational Reliability" in health
    assert "render_command_palette" in bootstrap
