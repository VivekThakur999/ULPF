"""MongoDB Pipeline Repository for saved pipeline debugger runs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import DESCENDING
from pymongo.database import Database

from app.core.mongodb import get_mongo_db
from app.models.common import new_uuid


class MongoPipelineRepository:
    """Handles debugger runs and stage traces in MongoDB."""

    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else get_mongo_db()
        self.pipeline_runs = self.db["pipeline_runs"]

    def save_run(self, run_dict: dict[str, Any]) -> str:
        doc = dict(run_dict)
        run_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = run_id
        if "id" in doc:
            del doc["id"]
        if "ts" not in doc:
            doc["ts"] = datetime.now(timezone.utc)
        self.pipeline_runs.insert_one(doc)
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        doc = self.pipeline_runs.find_one({"_id": run_id})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def list_runs(self, limit: int = 50, saved_only: bool = False) -> list[dict[str, Any]]:
        filter_doc = {"saved": True} if saved_only else {}
        cursor = self.pipeline_runs.find(filter_doc).sort("ts", DESCENDING).limit(limit)
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return items
