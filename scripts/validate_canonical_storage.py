from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.canonical_storage_validation_service import CanonicalStorageValidationService
from services.drive_path_service import DrivePathService
from services.json_service import JsonService
from utils.paths import APP_RUNTIME_DIR, BASE_DIR, DATA_DIR, GOVERNANCE_DIR, MANUFACTURERS_DIR


def main() -> int:
    service = CanonicalStorageValidationService(
        drive_path_service=DrivePathService(
            db_root=DATA_DIR / "MANDITRADE_DB",
            runtime_root=APP_RUNTIME_DIR,
            governance_root=GOVERNANCE_DIR,
            manufacturers_root=MANUFACTURERS_DIR,
            public_buyers_root=BASE_DIR / "data" / "public_buyers",
        ),
        json_service=JsonService(),
        governance_root=GOVERNANCE_DIR,
        public_buyers_root=BASE_DIR / "data" / "public_buyers",
    )
    report = service.validate()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in {"PASS", "REVIEW"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
