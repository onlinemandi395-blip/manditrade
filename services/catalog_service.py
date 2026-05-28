from __future__ import annotations

from pathlib import Path

import streamlit as st

from services.governance_service import GovernanceService


class CatalogService:
    def __init__(self, governance_root: Path) -> None:
        self.governance_root = governance_root

    @st.cache_data(show_spinner=False)
    def get_active_products(_self, governance_root: str) -> list[dict]:
        governance_service = GovernanceService(Path(governance_root), safe_drive_write_service=None)
        products = governance_service.list_products()
        return [
            product
            for product in products
            if product.get("status") == "ACTIVE"
            and product.get("visible", True)
            and product.get("mrp", 0) > 0
            and product.get("mandi_price", 0) >= 0
        ]

    def list_active_products(self) -> list[dict]:
        return self.get_active_products(str(self.governance_root))
