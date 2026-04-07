from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Session(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    ended_at: Optional[datetime] = Field(default=None, index=True)
    language: str = Field(default="en")
    mode: str = Field(default="practice")  # practice|interview|placement
    transcript: str = Field(default="")
    summary_json: str = Field(default="{}")  # compact storage for session summary


class MetricPoint(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(index=True)
    t_ms: int = Field(index=True)

    wpm: float = 0.0
    fillers_total: int = 0
    fillers_density: float = 0.0
    confidence: float = 0.0
    emotion: str = "neutral"
    eye_contact: float = 0.0
    posture: float = 0.0
    voice_variation: float = 0.0

