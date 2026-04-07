import base64
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas import ClientMessage, ServerMessage
from app.db_repo import append_session_event
from app.realtime.session import LiveSession

router = APIRouter()


@router.websocket("/ws/session")
async def ws_session(websocket: WebSocket):
    await websocket.accept()
    session = LiveSession()
    try:
        while True:
            raw = await websocket.receive_text()
            msg = ClientMessage.model_validate_json(raw)
            if msg.type == "session_start":
                mode = msg.payload.get("mode") if isinstance(msg.payload, dict) else None
                language = msg.payload.get("language") if isinstance(msg.payload, dict) else None
                session.reset(mode=str(mode or "practice"), language=str(language or "en"))
                if session.session_id is not None:
                    append_session_event(
                        session.session_id,
                        "session_start",
                        {"payload": msg.payload},
                    )
                # (mode is persisted in DB by create_session in reset; interview uses separate scoring endpoint)
                await websocket.send_text(
                    ServerMessage(type="ack", payload={"received_type": msg.type}).model_dump_json()
                )
                continue

            if msg.type == "session_stop":
                summary = session.finalize()
                if session.session_id is not None:
                    append_session_event(
                        session.session_id,
                        "session_stop",
                        {"summary": summary},
                    )
                await websocket.send_text(ServerMessage(type="session_saved", payload=summary).model_dump_json())
                continue

            if msg.type == "audio_chunk":
                b64 = msg.payload.get("pcm16_b64")
                sample_rate = int(msg.payload.get("sample_rate_hz", 16000))
                if not b64:
                    await websocket.send_text(
                        ServerMessage(type="error", payload={"message": "audio_chunk missing pcm16_b64"}).model_dump_json()
                    )
                    continue
                pcm16 = base64.b64decode(b64)
                now_ms = int(time.time() * 1000)
                if session.session_id is not None:
                    append_session_event(
                        session.session_id,
                        "audio_chunk",
                        {
                            "sample_rate_hz": sample_rate,
                            "bytes": len(pcm16),
                            "at_ms": now_ms,
                        },
                    )
                out_events = session.ingest_audio_pcm16(pcm16=pcm16, sample_rate_hz=sample_rate, now_ms=now_ms)
                for ev in out_events:
                    if session.session_id is not None and ev.type in ("realtime_metrics", "transcript_partial"):
                        append_session_event(
                            session.session_id,
                            ev.type,
                            ev.payload,
                        )
                    await websocket.send_text(ev.model_dump_json())
                continue

            if msg.type in ("video_landmarks", "video_frame"):
                if msg.type == "video_landmarks":
                    session.ingest_video_metrics(msg.payload)
                    if session.session_id is not None:
                        append_session_event(
                            session.session_id,
                            "video_landmarks",
                            msg.payload,
                        )
                await websocket.send_text(
                    ServerMessage(type="ack", payload={"received_type": msg.type}).model_dump_json()
                )
                continue

            await websocket.send_text(
                ServerMessage(type="error", payload={"message": f"unsupported message type: {msg.type}"}).model_dump_json()
            )
    except WebSocketDisconnect:
        return

