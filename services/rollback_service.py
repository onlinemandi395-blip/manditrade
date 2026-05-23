from __future__ import annotations

from pathlib import Path


class RollbackService:
    def __init__(self, safe_drive_write_service, logging_service) -> None:
        self.safe_drive_write_service = safe_drive_write_service
        self.logging_service = logging_service

    def restore_files(self, targets: list[Path]) -> None:
        for target in targets:
            restored = self.safe_drive_write_service.restore_latest_backup(target)
            if not restored:
                self.logging_service.log_error(
                    "transaction_failures",
                    "No backup available during rollback",
                    {"target": str(target)},
                )

    def remove_file_if_exists(self, target: Path) -> None:
        if target.exists():
            target.unlink(missing_ok=True)

