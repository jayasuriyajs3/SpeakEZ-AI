from __future__ import annotations

from pymongo import MongoClient, ReturnDocument
from pymongo.database import Database

from app.settings import settings

_client: MongoClient | None = None


def get_mongo_db() -> Database:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client[settings.mongodb_database]


def get_next_sequence(name: str) -> int:
    db = get_mongo_db()
    doc = db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["value"])
