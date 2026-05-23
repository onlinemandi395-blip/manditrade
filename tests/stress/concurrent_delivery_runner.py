from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.helpers.transaction_fixtures import build_order_service, build_runtime, current_user, seed_order


def main(iterations: int = 100) -> None:
    successes = 0
    failures = 0
    for index in range(iterations):
        run_root = Path(f"runtime/stress_delivery/run_{index:04d}")
        runtime = build_runtime(run_root)
        seed_order(runtime, "MANU101", status="DISPATCHED")
        service = build_order_service(runtime)
        try:
            service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", comments="ok")
            successes += 1
            try:
                service.confirm_delivery(current_user("MANU101"), "ORD-2026-000001", comments="duplicate")
                failures += 1
            except Exception:
                pass
        except Exception:
            failures += 1
    report = {"iterations": iterations, "successes": successes, "failures": failures, "scenario": "concurrent_delivery_runner"}
    target = Path("runtime/stress_reports/delivery_summary.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
