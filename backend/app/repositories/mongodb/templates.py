"""MongoDB Template Repository for log templates, matches, and compression benchmarks."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import DESCENDING
from pymongo.database import Database

from app.core.mongodb import get_mongo_db
from app.models.common import new_uuid


class MongoTemplateRepository:
    """Handles log templates, template matches, and compression records in MongoDB."""

    def __init__(self, db: Database | None = None):
        self.db = db if db is not None else get_mongo_db()
        self.templates = self.db["templates"]
        self.template_matches = self.db["template_matches"]
        self.compression_records = self.db["compression_records"]

    # --- Templates ---

    def upsert_template(self, tpl_dict: dict[str, Any]) -> dict[str, Any]:
        doc = dict(tpl_dict)
        sig = doc.get("token_signature")
        tpl_key = doc.get("template_key")
        tpl_id = str(doc.get("id") or doc.get("_id") or new_uuid())
        now = datetime.now(timezone.utc)
        doc["updated_at"] = now
        doc["_id"] = tpl_id
        if "id" in doc:
            del doc["id"]

        query_clauses: list[dict[str, Any]] = [{"_id": tpl_id}]
        if sig:
            query_clauses.append({"token_signature": sig})
        if tpl_key:
            query_clauses.append({"template_key": tpl_key})

        matching = list(self.templates.find({"$or": query_clauses}))
        if matching:
            primary = matching[0]
            actual_id = primary["_id"]
            # If matching existing doc has a different _id than incoming requested tpl_id,
            # remove the old docs so we can insert/update cleanly under tpl_id
            if str(actual_id) != str(tpl_id) or len(matching) > 1:
                all_old_ids = [m["_id"] for m in matching]
                self.templates.delete_many({"_id": {"$in": all_old_ids}})
                set_doc = {k: v for k, v in doc.items()}
                if "created_at" not in set_doc:
                    set_doc["created_at"] = primary.get("created_at", now)
                if "first_seen" not in set_doc:
                    set_doc["first_seen"] = primary.get("first_seen", now)
                if "last_seen" not in set_doc:
                    set_doc["last_seen"] = now
                self.templates.insert_one(set_doc)
                doc["id"] = tpl_id
                return doc
            else:
                set_doc = {k: v for k, v in doc.items() if k != "_id"}
                self.templates.update_one({"_id": actual_id}, {"$set": set_doc})
                updated = self.templates.find_one({"_id": actual_id})
                if updated:
                    updated["id"] = updated["_id"]
                return updated or {}

        if "created_at" not in doc:
            doc["created_at"] = now
        if "first_seen" not in doc:
            doc["first_seen"] = now
        if "last_seen" not in doc:
            doc["last_seen"] = now
        self.templates.insert_one(doc)
        doc["id"] = tpl_id
        return doc

    def get_template(self, tpl_id: Any) -> dict[str, Any] | None:
        doc = (
            self.templates.find_one({"_id": tpl_id})
            or (self.templates.find_one({"_id": int(tpl_id)}) if isinstance(tpl_id, str) and tpl_id.isdigit() else None)
            or (self.templates.find_one({"_id": str(tpl_id)}) if isinstance(tpl_id, int) else None)
            or self.templates.find_one({"template_key": str(tpl_id)})
            or self.templates.find_one({"token_signature": str(tpl_id)})
        )
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def get_template_by_key(self, template_key: str) -> dict[str, Any] | None:
        doc = self.templates.find_one({"template_key": template_key})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def get_template_by_signature(self, token_signature: str) -> dict[str, Any] | None:
        doc = self.templates.find_one({"token_signature": token_signature})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def list_templates(
        self,
        source: str | None = None,
        min_frequency: int = 1,
        time_from: datetime | None = None,
        time_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[dict[str, Any]], int, int, float]:
        filter_doc: dict[str, Any] = {"occurrences": {"$gte": min_frequency}}
        if time_from:
            filter_doc["last_seen"] = {"$gte": time_from}
        if time_to:
            filter_doc["first_seen"] = {"$lte": time_to}
        if source:
            filter_doc[f"source_distribution.{source}"] = {"$exists": True}

        all_matching = list(self.templates.find(filter_doc).sort("occurrences", DESCENDING))
        total = len(all_matching)
        covered_events = sum(r.get("occurrences", 0) for r in all_matching)

        sources: set[str] = set()
        for r in all_matching:
            sources.update((r.get("source_distribution") or {}).keys())

        total_vars = sum(r.get("variable_count", 0) for r in all_matching)
        avg_vars = round(total_vars / total, 2) if total else 0.0

        page = all_matching[offset : offset + limit]
        for item in page:
            item["id"] = item["_id"]

        return total, page, covered_events, len(sources), avg_vars

    def count_templates(self, filter_doc: dict[str, Any] | None = None) -> int:
        return self.templates.count_documents(filter_doc or {})

    # --- Template Matches ---

    def upsert_match(self, match_dict: dict[str, Any]) -> str:
        doc = dict(match_dict)
        raw_log_id = doc.get("raw_log_id")
        match_id = doc.get("id") or doc.get("_id") or new_uuid()
        if "id" in doc:
            del doc["id"]
        if "ts" not in doc:
            doc["ts"] = datetime.now(timezone.utc)

        if raw_log_id:
            set_doc = {k: v for k, v in doc.items() if k != "_id"}
            self.template_matches.update_one(
                {"raw_log_id": raw_log_id},
                {"$set": set_doc, "$setOnInsert": {"_id": match_id}},
                upsert=True,
            )
            return match_id

        doc["_id"] = match_id
        self.template_matches.insert_one(doc)
        return match_id

    def insert_matches_bulk(self, match_dicts: list[dict[str, Any]]) -> None:
        if not match_dicts:
            return
        now = datetime.now(timezone.utc)
        for m in match_dicts:
            doc = dict(m)
            raw_log_id = doc.get("raw_log_id")
            match_id = doc.get("id") or doc.get("_id") or new_uuid()
            if "id" in doc:
                del doc["id"]
            if "ts" not in doc:
                doc["ts"] = now
            if raw_log_id:
                set_doc = {k: v for k, v in doc.items() if k != "_id"}
                self.template_matches.update_one(
                    {"raw_log_id": raw_log_id},
                    {"$set": set_doc, "$setOnInsert": {"_id": match_id}},
                    upsert=True,
                )
            else:
                doc["_id"] = match_id
                self.template_matches.insert_one(doc)

    def get_match_by_raw_log_id(self, raw_log_id: str) -> dict[str, Any] | None:
        doc = self.template_matches.find_one({"raw_log_id": raw_log_id})
        if doc:
            doc["id"] = doc["_id"]
        return doc

    def get_matches_by_raw_log_ids(self, raw_log_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not raw_log_ids:
            return {}
        cursor = self.template_matches.find({"raw_log_id": {"$in": raw_log_ids}})
        out = {}
        for doc in cursor:
            doc["id"] = doc["_id"]
            out[doc["raw_log_id"]] = doc
        return out

    def list_matches_for_template(
        self, template_id: Any, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        id_str = str(template_id)
        conds = [{"template_id": template_id}, {"template_id": id_str}]
        if id_str.isdigit():
            conds.append({"template_id": int(id_str)})
        cursor = (
            self.template_matches.find({"$or": conds})
            .sort("ts", DESCENDING)
            .skip(max(0, offset))
            .limit(min(max(1, limit), 200))
        )
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return items

    # --- Compression Records ---

    def insert_compression_record(self, record_dict: dict[str, Any]) -> str:
        doc = dict(record_dict)
        rec_id = doc.get("id") or doc.get("_id") or new_uuid()
        doc["_id"] = rec_id
        if "id" in doc:
            del doc["id"]
        if "ts" not in doc:
            doc["ts"] = datetime.now(timezone.utc)
        self.compression_records.insert_one(doc)
        return rec_id

    def list_compression_records(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self.compression_records.find().sort("ts", DESCENDING).limit(limit)
        items = list(cursor)
        for item in items:
            item["id"] = item["_id"]
        return items
