from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

import streamlit as st

from services.id_service import IdService


class DataService:
    def __init__(self, cache_service) -> None:
        self.cache_service = cache_service
        self.id_service = IdService()
        st.session_state.setdefault("mt_next_data", {})

    def _bootstrap_collection(self, collection: str) -> list[dict]:
        cache_data = st.session_state["mt_next_data"]
        if collection in cache_data:
            return cache_data[collection]
        database_config = self.cache_service.get_config("database")
        source = database_config.get("collections", {}).get(collection, "")
        payload = []
        if ":" in source:
            config_name, key = source.split(":", 1)
            config_name = config_name.replace("configs/", "").replace(".json", "")
            payload = deepcopy(self.cache_service.get_config(config_name).get(key, []))
        cache_data[collection] = payload
        return cache_data[collection]

    def list_collection(self, collection: str) -> list[dict]:
        return list(self._bootstrap_collection(collection))

    def create_record(self, collection: str, values: dict) -> dict:
        rows = self._bootstrap_collection(collection)
        record = dict(values)
        record["id"] = self.id_service.next(collection.rstrip("s") or "record")
        record["created_at"] = datetime.now(UTC).isoformat()
        rows.append(record)
        return record
