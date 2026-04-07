from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session as DBSession, select

from app.db import engine
from app.db_models import MetricPoint, Session
from app.mongo import get_mongo_db, get_next_sequence
from app.settings import settings


@dataclass
class SessionRecord:
    id: int
    started_at: datetime
    ended_at: datetime | None
    language: str
    mode: str
    transcript: str
    summary_json: str


@dataclass
class MetricRecord:
    session_id: int
    t_ms: int
    wpm: float
    fillers_total: int
    fillers_density: float
    confidence: float
    emotion: str
    eye_contact: float
    posture: float
    voice_variation: float


def _use_mongodb() -> bool:
    return settings.storage_backend.strip().lower() == "mongodb"


def _session_doc_to_record(doc: dict) -> SessionRecord:
    return SessionRecord(
        id=int(doc["id"]),
        started_at=doc.get("started_at") or datetime.utcnow(),
        ended_at=doc.get("ended_at"),
        language=str(doc.get("language", "en")),
        mode=str(doc.get("mode", "practice")),
        transcript=str(doc.get("transcript", "") or ""),
        summary_json=json.dumps(doc.get("summary", {}), separators=(",", ":")),
    )


def _metric_doc_to_record(doc: dict) -> MetricRecord:
    return MetricRecord(
        session_id=int(doc["session_id"]),
        t_ms=int(doc.get("t_ms", 0) or 0),
        wpm=float(doc.get("wpm", 0) or 0),
        fillers_total=int(doc.get("fillers_total", 0) or 0),
        fillers_density=float(doc.get("fillers_density", 0) or 0),
        confidence=float(doc.get("confidence", 0) or 0),
        emotion=str(doc.get("emotion", "neutral") or "neutral"),
        eye_contact=float(doc.get("eye_contact", 0) or 0),
        posture=float(doc.get("posture", 0) or 0),
        voice_variation=float(doc.get("voice_variation", 0) or 0),
    )


def create_session(language: str = "en", mode: str = "practice") -> SessionRecord:
    if _use_mongodb():
        db = get_mongo_db()
        sid = get_next_sequence("sessions")
        now = datetime.now(timezone.utc)
        db.sessions.insert_one(
            {
                "id": sid,
                "started_at": now,
                "ended_at": None,
                "language": language,
                "mode": mode,
                "transcript": "",
                "summary": {},
                "events": [
                    {
                        "type": "session_created",
                        "at": now,
                        "payload": {"language": language, "mode": mode},
                    }
                ],
            }
        )
        return SessionRecord(
            id=sid,
            started_at=now,
            ended_at=None,
            language=language,
            mode=mode,
            transcript="",
            summary_json="{}",
        )

    s = Session(language=language, mode=mode, started_at=datetime.utcnow())
    with DBSession(engine) as db:
        db.add(s)
        db.commit()
        db.refresh(s)
        return SessionRecord(
            id=int(s.id or 0),
            started_at=s.started_at,
            ended_at=s.ended_at,
            language=s.language,
            mode=s.mode,
            transcript=s.transcript,
            summary_json=s.summary_json,
        )


def add_metric_point(session_id: int, p: dict) -> None:
    if _use_mongodb():
        db = get_mongo_db()
        db.metric_points.insert_one(
            {
                "session_id": int(session_id),
                "t_ms": int(p.get("t_ms", 0)),
                "wpm": float(p.get("wpm", 0) or 0),
                "fillers_total": int(p.get("fillers_total", 0) or 0),
                "fillers_density": float(p.get("fillers_density", 0) or 0),
                "confidence": float(p.get("confidence", 0) or 0),
                "emotion": str(p.get("emotion", "neutral") or "neutral"),
                "eye_contact": float(p.get("eye_contact", 0) or 0),
                "posture": float(p.get("posture", 0) or 0),
                "voice_variation": float(p.get("voice_variation", 0) or 0),
                "created_at": datetime.now(timezone.utc),
            }
        )
        return

    mp = MetricPoint(
        session_id=session_id,
        t_ms=int(p.get("t_ms", 0)),
        wpm=float(p.get("wpm", 0) or 0),
        fillers_total=int(p.get("fillers_total", 0) or 0),
        fillers_density=float(p.get("fillers_density", 0) or 0),
        confidence=float(p.get("confidence", 0) or 0),
        emotion=str(p.get("emotion", "neutral") or "neutral"),
        eye_contact=float(p.get("eye_contact", 0) or 0),
        posture=float(p.get("posture", 0) or 0),
        voice_variation=float(p.get("voice_variation", 0) or 0),
    )
    with DBSession(engine) as db:
        db.add(mp)
        db.commit()


def finalize_session(session_id: int, transcript: str, summary: dict) -> None:
    if _use_mongodb():
        db = get_mongo_db()
        now = datetime.now(timezone.utc)
        db.sessions.update_one(
            {"id": int(session_id)},
            {
                "$set": {
                    "ended_at": now,
                    "transcript": transcript,
                    "summary": summary,
                },
                "$push": {
                    "events": {
                        "type": "session_finalized",
                        "at": now,
                        "payload": {"summary": summary, "transcript_len": len(transcript or "")},
                    }
                },
            },
        )
        return

    with DBSession(engine) as db:
        s = db.exec(select(Session).where(Session.id == session_id)).one()
        s.ended_at = datetime.utcnow()
        s.transcript = transcript
        s.summary_json = json.dumps(summary, separators=(",", ":"))
        db.add(s)
        db.commit()


def list_sessions(limit: int = 50) -> list[SessionRecord]:
    if _use_mongodb():
        db = get_mongo_db()
        rows = db.sessions.find(
            {},
            {
                "_id": 0,
                "id": 1,
                "started_at": 1,
                "ended_at": 1,
                "language": 1,
                "mode": 1,
                "transcript": 1,
                "summary": 1,
            },
        ).sort("started_at", -1).limit(limit)
        return [_session_doc_to_record(r) for r in rows]

    with DBSession(engine) as db:
        rows = list(db.exec(select(Session).order_by(Session.started_at.desc()).limit(limit)))
        return [
            SessionRecord(
                id=int(s.id or 0),
                started_at=s.started_at,
                ended_at=s.ended_at,
                language=s.language,
                mode=s.mode,
                transcript=s.transcript,
                summary_json=s.summary_json,
            )
            for s in rows
        ]


def get_session(session_id: int) -> SessionRecord:
    if _use_mongodb():
        db = get_mongo_db()
        row = db.sessions.find_one(
            {"id": int(session_id)},
            {
                "_id": 0,
                "id": 1,
                "started_at": 1,
                "ended_at": 1,
                "language": 1,
                "mode": 1,
                "transcript": 1,
                "summary": 1,
            },
        )
        if not row:
            raise ValueError(f"session {session_id} not found")
        return _session_doc_to_record(row)

    with DBSession(engine) as db:
        s = db.exec(select(Session).where(Session.id == session_id)).one()
        return SessionRecord(
            id=int(s.id or 0),
            started_at=s.started_at,
            ended_at=s.ended_at,
            language=s.language,
            mode=s.mode,
            transcript=s.transcript,
            summary_json=s.summary_json,
        )


def get_metrics(session_id: int, limit: int = 1000) -> list[MetricRecord]:
    if _use_mongodb():
        db = get_mongo_db()
        q = db.metric_points.find({"session_id": int(session_id)}, {"_id": 0}).sort("t_ms", 1).limit(limit)
        return [_metric_doc_to_record(r) for r in q]

    with DBSession(engine) as db:
        q = select(MetricPoint).where(MetricPoint.session_id == session_id).order_by(MetricPoint.t_ms.asc()).limit(limit)
        rows = list(db.exec(q))
        return [
            MetricRecord(
                session_id=int(m.session_id),
                t_ms=int(m.t_ms),
                wpm=float(m.wpm),
                fillers_total=int(m.fillers_total),
                fillers_density=float(m.fillers_density),
                confidence=float(m.confidence),
                emotion=str(m.emotion),
                eye_contact=float(m.eye_contact),
                posture=float(m.posture),
                voice_variation=float(m.voice_variation),
            )
            for m in rows
        ]


def append_session_event(session_id: int, event_type: str, payload: dict | None = None) -> None:
    if not _use_mongodb():
        return
    db = get_mongo_db()
    db.sessions.update_one(
        {"id": int(session_id)},
        {
            "$push": {
                "events": {
                    "type": event_type,
                    "at": datetime.now(timezone.utc),
                    "payload": payload or {},
                }
            }
        },
    )


def get_session_events(session_id: int, limit: int = 2000) -> list[dict]:
    if not _use_mongodb():
        return []
    db = get_mongo_db()
    row = db.sessions.find_one({"id": int(session_id)}, {"_id": 0, "events": 1})
    events = list((row or {}).get("events") or [])
    return events[-limit:]

