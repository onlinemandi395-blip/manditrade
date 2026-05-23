from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.helpers.transaction_fixtures import build_procurement_service, build_runtime, current_user, seed_agreements, seed_inventory, seed_procurement_request


def main(iterations: int = 100) -> None:
    runtime = build_runtime(Path("runtime/stress_procurement"))
    successes = 0
    failures = 0
    for index in range(iterations):
        run_root = Path(f"runtime/stress_procurement/run_{index:04d}")
        runtime = build_runtime(run_root)
        seed_inventory(runtime, "MANU101", quantity=100)
        seed_procurement_request(runtime, "MANU101", request_id="REQ-2026-000001", requested_by="MANU999")
        seed_agreements(runtime, "MANU999")
        service = build_procurement_service(runtime)
        try:
            service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)
            failures += 0
            successes += 1
            try:
                service.accept_procurement_request(current_user("MANU101"), "REQ-2026-000001", unit_price=120.0, advance_amount=1200.0)
                failures += 1
            except Exception:
                pass
        except Exception:
            failures += 1
    report = {"iterations": iterations, "successes": successes, "failures": failures, "scenario": "concurrent_procurement_runner"}
    target = Path("runtime/stress_reports/procurement_summary.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
