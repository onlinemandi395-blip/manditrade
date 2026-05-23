from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class AgreementSettlementService:
    def confirm_settlement(self, agreement: dict[str, Any], amount: float, actor: str) -> dict[str, Any]:
        agreement["settlement"] = {
            "amount": round(amount, 2),
            "actor": actor,
            "settled_at": datetime.now(UTC).isoformat(),
            "status": "SETTLED",
        }
        agreement["status"] = "CLOSED"
        agreement["updated_at"] = datetime.now(UTC).isoformat()
        return agreement

