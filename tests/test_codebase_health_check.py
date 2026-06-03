from __future__ import annotations

import json

from scripts.codebase_health_check import build_report, main


def test_codebase_health_report_builds():
    report = build_report()

    assert "oversized_files" in report
    assert "duplicate_route_names" in report
    assert "hardcoded_role_string_files" in report
    assert "raw_large_html_card_candidates" in report
    assert "direct_inline_color_style_candidates" in report
    assert "raw_feedback_banner_candidates" in report
    assert "duplicate_search_bar_candidates" in report
    assert "direct_bulk_action_candidates" in report
    assert "raw_background_task_write_candidates" in report
    assert "retry_logic_outside_recovery_candidates" in report
    assert "raw_commerce_table_candidates" in report
    assert "missing_image_fallback_candidates" in report
    assert "missing_empty_state_candidates" in report
    assert "direct_drive_write_bypass_candidates" in report
    assert "random_admin_root_usage_candidates" in report


def test_codebase_health_script_writes_latest_report():
    target = main()
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert target.exists()
    assert "generated_at" in payload
    assert "python_files_scanned" in payload
