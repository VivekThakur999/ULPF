"""MongoDB Ingestion Repository for raw logs and processing jobs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.core.mongodb import get_mongo_db
from app.models.common import new_uuid


class MongoIngestionRepository:
    """Handles raw log storage and processing job lifecycle in MongoDB."""

    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else get_mongo_db()
        self.jobs = self.db["processing_jobs"]
        self.raw_logs = self.db["raw_logs"]

    # --- Processing Jobs ---

    def create_job(self, job_dict: dict[str, Any]) -> str:
        doc = dict(job_dict)
        job_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = job_id
        if "id" in doc:
            del doc["id"]
        if "created_at" not in doc:
            doc["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in doc:
            doc["updated_at"] = datetime.now(timezone.utc)
        self.jobs.insert_one(doc)
        return job_id

    def update_job(self, job_id: str, updates: dict[str, Any]) -> None:
        doc = dict(updates)
        doc["updated_at"] = datetime.now(timezone.utc)
        if "id" in doc:
            del doc["id"]
        if "_id" in doc:
            del doc["_id"]
        self.jobs.update_one({"_id": job_id}, {"$set": doc})

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        doc = self.jobs.find_one({"_id": job_id})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def list_jobs(
        self, limit: int = 50, offset: int = 0, status: str | None = None
    ) -> tuple[int, list[dict[str, Any]]]:
        filter_doc = {"status": status} if status else {}
        total = self.jobs.count_documents(filter_doc)
        cursor = (
            self.jobs.find(filter_doc)
            .sort("created_at", DESCENDING)
            .skip(max(0, offset))
            .limit(min(max(1, limit), 200))
        )
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return total, items

    def count_jobs(self, filter_doc: dict[str, Any] | None = None) -> int:
        return self.jobs.count_documents(filter_doc or {})

    # --- Raw Logs ---

    def insert_raw_log(self, raw_dict: dict[str, Any]) -> str:
        doc = dict(raw_dict)
        raw_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = raw_id
        if "id" in doc:
            del doc["id"]
        if "received_at" not in doc:
            doc["received_at"] = datetime.now(timezone.utc)
        self.raw_logs.insert_one(doc)
        return raw_id

    def insert_raw_logs_bulk(self, raw_dicts: list[dict[str, Any]]) -> list[str]:
        if not raw_dicts:
            return []
        docs = []
        ids = []
        now = datetime.now(timezone.utc)
        for r in raw_dicts:
            doc = dict(r)
            raw_id = doc.get("id") or doc.get("_id") or new_uuid()
            doc["_id"] = raw_id
            if "id" in doc:
                del doc["id"]
            if "received_at" not in doc:
                doc["received_at"] = now
            docs.append(doc)
            ids.append(raw_id)
        self.raw_logs.insert_many(docs, ordered=False)
        return ids

    def get_raw_log(self, raw_log_id: str) -> dict[str, Any] | None:
        doc = self.raw_logs.find_one({"_id": raw_log_id})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def get_raw_logs_by_ids(self, raw_log_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not raw_log_ids:
            return {}
        cursor = self.raw_logs.find({"_id": {"$in": raw_log_ids}})
        out = {}
        for doc in cursor:
            doc["id"] = doc["_id"]
            out[doc["_id"]] = doc
        return out

    def list_raw_logs(
        self,
        job_id: str | None = None,
        source_name: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        filter_doc: dict[str, Any] = {}
        if job_id:
            filter_doc["job_id"] = job_id
        if source_name:
            filter_doc["source_name"] = source_name
        if status:
            filter_doc["status"] = status

        total = self.raw_logs.count_documents(filter_doc)
        cursor = (
            self.raw_logs.find(filter_doc)
            .sort([("line_number", ASCENDING), ("received_at", ASCENDING)])
            .skip(max(0, offset))
            .limit(min(max(1, limit), 500))
        )
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return total, items

    def count_raw_logs(self, filter_doc: dict[str, Any] | None = None) -> int:
        return self.raw_logs.count_documents(filter_doc or {})
