from __future__ import annotations

import os

import pytest


RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS", "").lower() == "true"


def pytest_collection_modifyitems(config, items):
    if RUN_INTEGRATION_TESTS:
        return
    skip_marker = pytest.mark.skip(reason="Set RUN_INTEGRATION_TESTS=true to run integration tests.")
    for item in items:
        if "tests/integration/" in str(item.fspath).replace("\\", "/"):
            item.add_marker(skip_marker)
