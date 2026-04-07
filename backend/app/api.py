from __future__ import annotations

import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.db_repo import get_metrics, get_session, get_session_events, list_sessions
from app.interview.questions import QUESTIONS
from app.interview.scoring import score_content, score_overall

router = APIRouter(prefix="/api")


def _to_iso_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_local_text(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


@router.get("/sessions")
def sessions():
    rows = list_sessions()
    return [
        {
            "id": s.id,
            "started_at": _to_iso_utc(s.started_at),
            "ended_at": _to_iso_utc(s.ended_at),
            "language": s.language,
            "mode": s.mode,
        }
        for s in rows
    ]


@router.get("/sessions/{session_id}")
def session_detail(session_id: int):
    s = get_session(session_id)
    metrics = get_metrics(session_id, limit=2000)
    events = get_session_events(session_id, limit=5000)
    return {
        "id": s.id,
        "started_at": _to_iso_utc(s.started_at),
        "ended_at": _to_iso_utc(s.ended_at),
        "language": s.language,
        "mode": s.mode,
        "transcript": s.transcript,
        "summary": json.loads(s.summary_json or "{}"),
        "events": events,
        "metrics": [
            {
                "t_ms": m.t_ms,
                "wpm": m.wpm,
                "fillers_total": m.fillers_total,
                "fillers_density": m.fillers_density,
                "confidence": m.confidence,
                "emotion": m.emotion,
                "eye_contact": m.eye_contact,
                "posture": m.posture,
                "voice_variation": m.voice_variation,
            }
            for m in metrics
        ],
    }


@router.get("/interview/questions")
def interview_questions():
    return QUESTIONS


@router.post("/interview/score")
def interview_score(payload: dict):
    answer = str(payload.get("answer", "") or "")
    confidence = float(payload.get("confidence", 0) or 0)
    content = score_content(answer)
    overall = score_overall(content, confidence)
    return {"content": round(content, 1), "overall": round(overall, 1)}


@router.get("/sessions/{session_id}/report.pdf")
def session_pdf(session_id: int):
    s = get_session(session_id)
    metrics = get_metrics(session_id, limit=2000)
    last = metrics[-1] if metrics else None

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    y = h - 60

    c.setFont("Helvetica-Bold", 16)
    c.drawString(48, y, f"SPEAKEZ AI – Session Report #{s.id}")
    y -= 28

    c.setFont("Helvetica", 10)
    c.drawString(48, y, f"Started: {_to_local_text(s.started_at)}   Ended: {_to_local_text(s.ended_at)}   Lang: {s.language}")
    y -= 20

    if last:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(48, y, "Summary")
        y -= 16
        c.setFont("Helvetica", 10)
        c.drawString(48, y, f"WPM: {last.wpm:.1f}   Fillers: {last.fillers_total}   Confidence: {last.confidence:.1f}")
        y -= 14
        c.drawString(48, y, f"Eye contact: {last.eye_contact*100:.0f}%   Posture: {last.posture*100:.0f}%   Emotion: {last.emotion}")
        y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(48, y, "Transcript (truncated)")
    y -= 16
    c.setFont("Helvetica", 9)
    text = (s.transcript or "").strip()
    if len(text) > 1400:
        text = text[:1400] + "…"
    for line in wrap_text(text, max_chars=110):
        if y < 80:
            c.showPage()
            y = h - 60
            c.setFont("Helvetica", 9)
        c.drawString(48, y, line)
        y -= 12

    c.showPage()
    c.save()
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf")


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        if sum(len(x) for x in cur) + len(cur) + len(w) > max_chars:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines

