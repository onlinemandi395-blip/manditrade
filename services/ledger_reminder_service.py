from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any


class LedgerReminderService:
    def __init__(self, gmail_service, ledger_service, safe_drive_write_service, domain_paths_service, json_service, config: dict[str, Any]) -> None:
        self.gmail_service = gmail_service
        self.ledger_service = ledger_service
        self.safe_drive_write_service = safe_drive_write_service
        self.domain_paths = domain_paths_service
        self.json_service = json_service
        self.config = config

    def run_for_manufacturer(self, manufacturer_code: str, recipient_email: str) -> int:
        reminder_cfg = self.config.get("ledger_reminders", {})
        if not reminder_cfg.get("enabled", False):
            return 0
        path = self.domain_paths.ledger_path(manufacturer_code)
        payload = self.json_service.read_json(path, {"ledgers": []})
        today = date.today()
        queued = 0

        def classify(due_date_str: str) -> str | None:
            due_date = date.fromisoformat(due_date_str)
            delta = (due_date - today).days
            if delta == reminder_cfg.get("upcoming_days_before", 3):
                return "UPCOMING_DUE"
            if delta == 0:
                return "DUE_TODAY"
            if delta < 0 and abs(delta) >= reminder_cfg.get("final_reminder_after_days", 15):
                return "FINAL_REMINDER"
            if delta < 0:
                return "OVERDUE"
            return None

        for ledger in payload.get("ledgers", []):
            for entry in ledger.get("entries", []):
                if entry.get("status") == "PAID":
                    continue
                reminder_type = classify(entry["due_date"])
                if not reminder_type:
                    continue
                sent = entry.setdefault("reminders_sent", [])
                if reminder_type in sent:
                    continue
                if len(sent) >= reminder_cfg.get("max_reminders_per_due", 4):
                    continue
                self.gmail_service.enqueue_message(
                    to_email=recipient_email,
                    subject=f"Ledger Reminder: {reminder_type}",
                    body=f"Ledger {ledger['ledger_id']} has due entry {entry['entry_id']} with balance Rs {entry['balance_due']}.",
                    notification_type="ledger_reminder",
                )
                sent.append(reminder_type)
                entry["last_reminder_at"] = datetime.now(UTC).isoformat()
                queued += 1

        self.safe_drive_write_service.replace_document(path, payload)
        return queued
