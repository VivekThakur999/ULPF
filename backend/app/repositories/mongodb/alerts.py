"""MongoDB Alert Repository for security alerts, incidents, and security events."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import DESCENDING
from pymongo.database import Database

from app.core.mongodb import get_mongo_db
from app.models.common import new_uuid


class MongoAlertRepository:
    """Handles security alerts and security shield events in MongoDB."""

    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else get_mongo_db()
        self.alerts = self.db["security_alerts"]
        self.security_events = self.db["security_events"]

    # --- Security Alerts ---

    def upsert_alert(self, alert_dict: dict[str, Any]) -> dict[str, Any]:
        doc = dict(alert_dict)
        dedup_key = doc.get("dedup_key")
        now = datetime.now(timezone.utc)
        doc["updated_at"] = now

        if dedup_key:
            existing = self.alerts.find_one({"dedup_key": dedup_key})
            if existing:
                alert_id = existing["_id"]
                if "id" in doc:
                    del doc["id"]
                if "_id" in doc:
                    del doc["_id"]
                self.alerts.update_one({"_id": alert_id}, {"$set": doc})
                updated = self.alerts.find_one({"_id": alert_id})
                if updated:
                    updated["id"] = updated["_id"]
                return updated or {}

        alert_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = alert_id
        if "id" in doc:
            del doc["id"]
        if "ts" not in doc:
            doc["ts"] = now
        self.alerts.insert_one(doc)
        doc["id"] = alert_id
        return doc

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        doc = self.alerts.find_one({"_id": alert_id})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def get_alert_by_dedup_key(self, dedup_key: str) -> dict[str, Any] | None:
        doc = self.alerts.find_one({"dedup_key": dedup_key})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def list_alerts(
        self,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]]]:
        filter_doc: dict[str, Any] = {}
        if status:
            filter_doc["status"] = status.upper()
        if severity:
            filter_doc["severity"] = severity.lower()

        total = self.alerts.count_documents(filter_doc)
        cursor = (
            self.alerts.find(filter_doc)
            .sort([("risk_score", DESCENDING), ("ts", DESCENDING)])
            .skip(max(0, offset))
            .limit(min(max(1, limit), 200))
        )
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return total, items

    def update_alert(self, alert_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        doc = dict(updates)
        doc["updated_at"] = datetime.now(timezone.utc)
        if "id" in doc:
            del doc["id"]
        if "_id" in doc:
            del doc["_id"]
        result = self.alerts.update_one({"_id": alert_id}, {"$set": doc})
        if result.matched_count == 0:
            return None
        updated = self.alerts.find_one({"_id": alert_id})
        if updated:
            updated["id"] = updated["_id"]
        return updated

    def count_alerts(self, filter_doc: dict[str, Any] | None = None) -> int:
        return self.alerts.count_documents(filter_doc or {})

    def group_count_alerts(
        self, field_name: str, filter_doc: dict[str, Any] | None = None, limit: int = 15
    ) -> list[dict]:
        match = {**(filter_doc or {}), field_name: {"$exists": True, "$ne": None}}
        pipeline = [
            {"$match": match},
            {"$group": {"_id": f"${field_name}", "value": {"$sum": 1}}},
            {"$sort": {"value": -1}},
            {"$limit": limit},
            {"$project": {"label": {"$toString": "$_id"}, "value": 1, "_id": 0}},
        ]
        try:
            return list(self.alerts.aggregate(pipeline))
        except Exception:
            counts: dict[str, int] = {}
            for doc in self.alerts.find(match, {field_name: 1}):
                val = str(doc.get(field_name))
                if val:
                    counts[val] = counts.get(val, 0) + 1
            sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"label": k, "value": v} for k, v in sorted_items]

    # --- Security Events (Shield Verdicts) ---

    def insert_security_event(self, event_dict: dict[str, Any]) -> str:
        doc = dict(event_dict)
        sec_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = sec_id
        if "id" in doc:
            del doc["id"]
        if "ts" not in doc:
            doc["ts"] = datetime.now(timezone.utc)
        self.security_events.insert_one(doc)
        return sec_id

    def insert_security_events_bulk(self, event_dicts: list[dict[str, Any]]) -> list[str]:
        if not event_dicts:
            return []
        docs = []
        ids = []
        now = datetime.now(timezone.utc)
        for e in event_dicts:
            doc = dict(e)
            sec_id = doc.get("id") or doc.get("_id") or new_uuid()
            doc["_id"] = sec_id
            if "id" in doc:
                del doc["id"]
            if "ts" not in doc:
                doc["ts"] = now
            docs.append(doc)
            ids.append(sec_id)
        self.security_events.insert_many(docs, ordered=False)
        return ids

    def list_security_events(
        self,
        job_id: str | None = None,
        raw_reference: str | None = None,
        verdict: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        filter_doc: dict[str, Any] = {}
        if job_id:
            filter_doc["job_id"] = job_id
        if raw_reference:
            filter_doc["raw_reference"] = raw_reference
        if verdict:
            filter_doc["verdict"] = verdict

        cursor = self.security_events.find(filter_doc).sort("ts", DESCENDING).limit(limit)
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return items

    def count_security_events(self, filter_doc: dict[str, Any] | None = None) -> int:
        return self.security_events.count_documents(filter_doc or {})
