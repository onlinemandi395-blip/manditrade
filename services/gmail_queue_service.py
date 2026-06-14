from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import streamlit as st

from services.id_service import IdService


class GmailQueueService:
    def __init__(self, data_service: Any = None) -> None:
        self.data_service = data_service
        self.id_service = IdService()

    def is_enabled(self) -> bool:
        section = dict(st.secrets.get("gmail", {})) if "gmail" in st.secrets else {}
        return bool(section.get("enabled", False))

    def get_sender_email(self) -> str:
        section = dict(st.secrets.get("gmail", {})) if "gmail" in st.secrets else {}
        return str(section.get("sender_email", "")).strip()

    def enqueue(self, *, to_email: str, subject: str, body: str, notification_id: str = "") -> dict:
        record = {
            "queue_id": self.id_service.next("gmail_queue"),
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "notification_id": notification_id,
            "status": "QUEUED",
            "created_at": datetime.now(UTC).isoformat(),
            "attempt_count": 0,
        }
        if self.data_service is not None:
            self.data_service._bootstrap_collection("gmail_queue").append(record)
        return record
