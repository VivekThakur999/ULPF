"""MongoDB Response Repository for virtual response simulations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import DESCENDING
from pymongo.database import Database

from app.core.mongodb import get_mongo_db
from app.models.common import new_uuid


class MongoResponseRepository:
    """Handles virtual response simulation records in MongoDB."""

    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else get_mongo_db()
        self.simulations = self.db["response_simulations"]

    def save_simulation(self, sim_dict: dict[str, Any]) -> str:
        doc = dict(sim_dict)
        sim_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = sim_id
        if "id" in doc:
            del doc["id"]
        if "ts" not in doc:
            doc["ts"] = datetime.now(timezone.utc)
        doc["simulation_only"] = True  # Strict invariant
        self.simulations.insert_one(doc)
        return sim_id

    def get_simulation(self, sim_id: str) -> dict[str, Any] | None:
        doc = self.simulations.find_one({"_id": sim_id})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def list_simulations(
        self, alert_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        filter_doc = {"alert_id": alert_id} if alert_id else {}
        cursor = self.simulations.find(filter_doc).sort("ts", DESCENDING).limit(limit)
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return items
