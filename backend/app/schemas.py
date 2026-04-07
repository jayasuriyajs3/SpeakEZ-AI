from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ClientMessageType = Literal[
    "session_start",
    "session_stop",
    "audio_chunk",
    "video_landmarks",
    "video_frame",
]

ServerMessageType = Literal[
    "ack",
    "realtime_metrics",
    "transcript_partial",
    "transcript_final",
    "session_saved",
    "error",
]


class ClientMessage(BaseModel):
    type: ClientMessageType
    payload: dict[str, Any] = Field(default_factory=dict)


class ServerMessage(BaseModel):
    type: ServerMessageType
    payload: dict[str, Any] = Field(default_factory=dict)

