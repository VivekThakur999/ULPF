"""MongoDB-backed Event Repository for querying, searching, and aggregating normalized events."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Sequence

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.core.mongodb import get_mongo_db
from app.models.common import new_uuid
from app.models.event import NormalizedEvent
from app.repositories.events import EventPage, EventQuery


def doc_to_normalized_event(doc: dict[str, Any]) -> NormalizedEvent:
    doc_id = doc.get("id") or doc.get("_id") or ""
    return NormalizedEvent(
        id=doc_id,
        job_id=doc.get("job_id"),
        raw_log_id=doc.get("raw_log_id"),
        ingested_at=doc.get("ingested_at"),
        timestamp=doc.get("timestamp"),
        source=doc.get("source", "unknown"),
        host=doc.get("host"),
        event_type=doc.get("event_type"),
        severity=doc.get("severity"),
        username=doc.get("username"),
        email=doc.get("email"),
        source_ip=doc.get("source_ip"),
        destination_ip=doc.get("destination_ip"),
        source_port=doc.get("source_port"),
        destination_port=doc.get("destination_port"),
        protocol=doc.get("protocol"),
        action=doc.get("action"),
        status=doc.get("status"),
        process=doc.get("process"),
        service=doc.get("service"),
        url=doc.get("url"),
        http_method=doc.get("http_method"),
        response_code=doc.get("response_code"),
        message=doc.get("message", ""),
        extra=doc.get("extra") if isinstance(doc.get("extra"), dict) else {},
        field_confidence=doc.get("field_confidence") if isinstance(doc.get("field_confidence"), dict) else {},
        raw_log=doc.get("raw_log", ""),
        parser=doc.get("parser", "unknown"),
        parser_version=doc.get("parser_version", "0.0"),
        schema_version=doc.get("schema_version", "1.0"),
        pii_protected=bool(doc.get("pii_protected", False)),
        pii_mode=doc.get("pii_mode", "OFF"),
        processing_status=doc.get("processing_status", "ok"),
        confidence=float(doc.get("confidence", 0.0) or 0.0),
        template_id=doc.get("template_id"),
        created_at=doc.get("created_at") or doc.get("ingested_at"),
    )


class MongoEventRepository:
    """MongoDB implementation of the Universal Log Event repository."""

    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else get_mongo_db()
        self.collection = self.db["normalized_events"]

    def _build_filter(self, q: EventQuery) -> dict[str, Any]:
        conds: dict[str, Any] = {}

        if q.text:
            text_escaped = re.escape(q.text)
            regex = {"$regex": text_escaped, "$options": "i"}
            conds["$or"] = [
                {"message": regex},
                {"raw_log": regex},
                {"host": regex},
                {"username": regex},
                {"source_ip": regex},
                {"url": regex},
                {"process": regex},
            ]

        # Time range
        time_cond: dict[str, Any] = {}
        if q.time_from:
            time_cond["$gte"] = q.time_from
        if q.time_to:
            time_cond["$lte"] = q.time_to
        if time_cond:
            conds["timestamp"] = time_cond

        # Field equality
        for field, val in (
            ("source", q.source),
            ("host", q.host),
            ("source_ip", q.source_ip),
            ("destination_ip", q.destination_ip),
            ("username", q.username),
            ("event_type", q.event_type),
            ("severity", q.severity),
            ("action", q.action),
            ("status", q.status),
            ("parser", q.parser),
            ("processing_status", q.processing_status),
            ("job_id", q.job_id),
            ("template_id", q.template_id),
        ):
            if val is not None:
                conds[field] = val

        if q.any_ip:
            ip_cond = [{"source_ip": q.any_ip}, {"destination_ip": q.any_ip}]
            if "$or" in conds:
                conds = {"$and": [{"$or": conds.pop("$or")}, {"$or": ip_cond}], **conds}
            else:
                conds["$or"] = ip_cond

        # In list
        for fname, values in q.fields_in.items():
            if values:
                m_field = "_id" if fname == "id" else fname
                conds[m_field] = {"$in": list(values)}

        return conds

    def search(self, q: EventQuery) -> EventPage:
        filter_doc = self._build_filter(q)
        total = self.collection.count_documents(filter_doc)

        sort_dir = DESCENDING if q.order == "desc" else ASCENDING
        cursor = (
            self.collection.find(filter_doc)
            .sort([("timestamp", sort_dir), ("ingested_at", DESCENDING)])
            .skip(max(0, q.offset))
            .limit(min(max(1, q.limit), 10000))
        )

        items = [doc_to_normalized_event(item) for item in cursor]
        return EventPage(total=total, items=items)

    def get(self, event_id: str) -> NormalizedEvent | None:
        doc = self.collection.find_one({"_id": event_id})
        if doc:
            return doc_to_normalized_event(doc)
        return None

    def facets(self, q: EventQuery, fields: Sequence[str]) -> dict[str, list[dict]]:
        filter_doc = self._build_filter(q)
        out: dict[str, list[dict]] = {}

        for fname in fields:
            pipeline = [
                {"$match": {**filter_doc, fname: {"$exists": True, "$ne": None}}},
                {"$group": {"_id": f"${fname}", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 20},
                {"$project": {"value": "$_id", "count": 1, "_id": 0}},
            ]
            try:
                results = list(self.collection.aggregate(pipeline))
                out[fname] = results
            except Exception:
                out[fname] = []

        return out

    def timeseries(self, q: EventQuery, *, bucket: str = "hour") -> list[dict]:
        filter_doc = self._build_filter(q)
        match_filter = {**filter_doc, "timestamp": {"$exists": True, "$ne": None}}

        fmt = {
            "minute": "%Y-%m-%dT%H:%M",
            "hour": "%Y-%m-%dT%H:00:00",
            "day": "%Y-%m-%d",
        }.get(bucket, "%Y-%m-%dT%H:00:00")

        pipeline = [
            {"$match": match_filter},
            {
                "$project": {
                    "bucket": {
                        "$dateToString": {
                            "format": fmt,
                            "date": "$timestamp",
                        }
                    }
                }
            },
            {"$group": {"_id": "$bucket", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$project": {"bucket": "$_id", "count": 1, "_id": 0}},
        ]

        try:
            results = list(self.collection.aggregate(pipeline))
            return results
        except Exception:
            # Fallback for mock environments that do not support $dateToString
            all_events = self.collection.find(match_filter, {"timestamp": 1})
            counts: dict[str, int] = {}
            for e in all_events:
                ts = e.get("timestamp")
                if isinstance(ts, datetime):
                    bkt_str = ts.strftime(fmt.replace("%Y", "%Y").replace("%m", "%m").replace("%d", "%d"))
                    counts[bkt_str] = counts.get(bkt_str, 0) + 1
                elif isinstance(ts, str):
                    counts[ts[:13] + ":00:00" if bucket == "hour" else ts[:10]] = counts.get(ts, 0) + 1
            return [{"bucket": k, "count": v} for k, v in sorted(counts.items())]

    def distinct_values(self, field_name: str, q: EventQuery | None = None) -> list[str]:
        filter_doc = self._build_filter(q) if q else {}
        values = self.collection.distinct(field_name, filter_doc)
        return [str(v) for v in values if v is not None][:200]

    def insert(self, event: dict[str, Any]) -> str:
        doc = dict(event)
        doc_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = doc_id
        if "id" in doc:
            del doc["id"]
        if "ingested_at" not in doc:
            doc["ingested_at"] = datetime.now(timezone.utc)
        self.collection.insert_one(doc)
        return doc_id

    def insert_bulk(self, events: list[dict[str, Any]]) -> list[str]:
        if not events:
            return []
        docs = []
        ids = []
        for ev in events:
            doc = dict(ev)
            doc_id = doc.get("id") or doc.get("_id") or new_uuid()
            doc["_id"] = doc_id
            if "id" in doc:
                del doc["id"]
            if "ingested_at" not in doc:
                doc["ingested_at"] = datetime.now(timezone.utc)
            docs.append(doc)
            ids.append(doc_id)
        self.collection.insert_many(docs, ordered=False)
        return ids

    def count(self, filter_doc: dict[str, Any] | None = None) -> int:
        return self.collection.count_documents(filter_doc or {})

    def group_count(self, field_name: str, filter_doc: dict[str, Any] | None = None, limit: int = 15) -> list[dict]:
        match = {**(filter_doc or {}), field_name: {"$exists": True, "$ne": None}}
        pipeline = [
            {"$match": match},
            {"$group": {"_id": f"${field_name}", "value": {"$sum": 1}}},
            {"$sort": {"value": -1}},
            {"$limit": limit},
            {"$project": {"label": {"$toString": "$_id"}, "value": 1, "_id": 0}},
        ]
        try:
            return list(self.collection.aggregate(pipeline))
        except Exception:
            # Fallback for mock environments
            counts: dict[str, int] = {}
            for doc in self.collection.find(match, {field_name: 1}):
                val = str(doc.get(field_name))
                if val:
                    counts[val] = counts.get(val, 0) + 1
            sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
            return [{"label": k, "value": v} for k, v in sorted_items]
