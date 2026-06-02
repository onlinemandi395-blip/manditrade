from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.paths import APP_RUNTIME_DIR, BASE_DIR, GOVERNANCE_DIR


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _count_marketplace_orders() -> int:
    root = BASE_DIR / "data" / "public_orders"
    if not root.exists():
        return 0
    return len(list(root.rglob("*.json")))


def _count_public_payments() -> int:
    root = BASE_DIR / "data" / "public_payments"
    if not root.exists():
        return 0
    return len(list(root.rglob("*.json")))


def _manufacturer_ledger_counts() -> tuple[int, int]:
    ledger_files = list((BASE_DIR / "data" / "manufacturers").rglob("ledgers.json"))
    ledger_books = 0
    ledger_entries = 0
    for path in ledger_files:
        payload = _read_json(path, {"ledgers": []})
        ledgers = payload.get("ledgers", [])
        ledger_books += len(ledgers)
        for ledger in ledgers:
            ledger_entries += len(ledger.get("entries", []))
    return ledger_books, ledger_entries


def _count_critical_alerts() -> list[dict[str, Any]]:
    alerts_path = APP_RUNTIME_DIR / "alerts" / "alerts.json"
    payload = _read_json(alerts_path, {"alerts": []})
    return [
        item
        for item in payload.get("alerts", [])
        if str(item.get("severity", "")).upper() == "CRITICAL" and not bool(item.get("resolved", False))
    ]


def _latest_release_env() -> dict[str, Any]:
    return _read_json(APP_RUNTIME_DIR / "release_reports" / "latest_release_env.json", {})


def build_snapshot() -> dict[str, Any]:
    manufacturers = _read_json(GOVERNANCE_DIR / "manufacturers.json", {"manufacturers": []}).get("manufacturers", [])
    products = _read_json(GOVERNANCE_DIR / "products.json", {"products": []}).get("products", [])
    mahajans = _read_json(GOVERNANCE_DIR / "mahajans.json", {"mahajans": []}).get("mahajans", [])
    raw_materials = _read_json(GOVERNANCE_DIR / "raw_materials.json", {"raw_materials": []}).get("raw_materials", [])
    supply_orders = _read_json(GOVERNANCE_DIR / "supply_orders.json", {"supply_orders": []}).get("supply_orders", [])
    supply_ledgers = _read_json(GOVERNANCE_DIR / "supply_ledgers.json", {"entries": []}).get("entries", [])
    workers = _read_json(GOVERNANCE_DIR / "workers.json", {"workers": []}).get("workers", [])
    jobs_payload = _read_json(GOVERNANCE_DIR / "jobs.json", {"jobs": [], "applications": []})
    public_buyers_root = BASE_DIR / "data" / "public_buyers"
    public_buyer_count = len(list(public_buyers_root.rglob("*.json"))) if public_buyers_root.exists() else 0
    ledger_books, ledger_entries = _manufacturer_ledger_counts()
    critical_alerts = _count_critical_alerts()
    latest_env = _latest_release_env()

    recommendation = "GO"
    reasons: list[str] = []
    if latest_env.get("status") == "FAIL":
        recommendation = "NO_GO"
        reasons.append("Release environment validation is failing.")
    if critical_alerts:
        recommendation = "NO_GO"
        reasons.append("Unresolved critical alerts exist.")
    elif any(str(item.get("status", "")).upper() == "OVERDUE" for item in supply_ledgers):
        recommendation = "GO_WITH_CAUTION"
        reasons.append("Overdue supply-ledger entries require operator attention.")

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "role_counts": {
            "platform_admin": len(_read_json(GOVERNANCE_DIR / "admin_profiles.json", {"profiles": []}).get("profiles", [])),
            "manufacturer": len(manufacturers),
            "mahajan": len(mahajans),
            "public_buyer": public_buyer_count,
            "worker": len(workers),
        },
        "order_counts": {
            "marketplace_orders": _count_marketplace_orders(),
            "mandi_orders": len(supply_orders),
            "job_posts": len(jobs_payload.get("jobs", [])),
            "job_applications": len(jobs_payload.get("applications", [])),
        },
        "product_counts": {
            "products": len(products),
            "raw_materials": len(raw_materials),
        },
        "payment_counts": {
            "public_payment_submissions": _count_public_payments(),
            "supply_ledger_entries": len(supply_ledgers),
        },
        "ledger_counts": {
            "manufacturer_ledgers": ledger_books,
            "manufacturer_ledger_entries": ledger_entries,
        },
        "alert_counts": {
            "critical_open": len(critical_alerts),
            "release_env_status": latest_env.get("status", "UNKNOWN"),
        },
        "unresolved_critical_issues": [
            {"entity_type": item.get("entity_type", ""), "entity_id": item.get("entity_id", ""), "message": item.get("message", "")}
            for item in critical_alerts[:25]
        ],
        "release_recommendation": recommendation,
        "reasons": reasons,
    }


def main() -> int:
    snapshot = build_snapshot()
    target_dir = APP_RUNTIME_DIR / "release_snapshots"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = target_dir / f"release_snapshot_{timestamp}.json"
    target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Release snapshot written to {target}")
    print(f"Recommendation: {snapshot['release_recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
