from __future__ import annotations

import json

from scripts.codebase_health_check import build_report, main


def test_codebase_health_report_builds():
    report = build_report()

    assert "oversized_files" in report
    assert "duplicate_route_names" in report
    assert "hardcoded_role_string_files" in report


def test_codebase_health_script_writes_latest_report():
    target = main()
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert target.exists()
    assert "generated_at" in payload
    assert "python_files_scanned" in payload
