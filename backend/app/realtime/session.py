from __future__ import annotations

import io
import wave
from dataclasses import dataclass, field
from typing import List

import numpy as np

from app.schemas import ServerMessage
from app.pipelines.audio import AudioPipeline, suggestions_for
from app.ml.voice import compute_voice_variation
from app.nlp.insights import generate_insights
from app.db_repo import add_metric_point, create_session, finalize_session
from app.ml.confidence import ConfidenceFeatures, ConfidenceModel, DEFAULT_MODEL_PATH


@dataclass
class LiveSession:
    """
    Keeps lightweight, realtime session state in memory.

    This is intentionally simple: it buffers PCM16 mono audio and periodically emits
    placeholder metrics + transcript events. The next todos replace placeholders with:
    - VAD gating
    - Whisper transcription
    - filler/WPM/confidence/voice features
    """

    sample_rate_hz: int = 16000
    pcm16: bytearray = field(default_factory=bytearray)
    last_emit_ms: int = 0
    last_transcribe_ms: int = 0
    last_transcribed_bytes: int = 0
    transcript: str = ""
    language: str | None = "en"
    audio: AudioPipeline = field(default_factory=AudioPipeline)
    eye_contact: float = 0.0
    posture: float = 0.0
    emotion: str = "neutral"
    voice_variation: float = 0.0
    history: list[dict] = field(default_factory=list)
    session_id: int | None = None
    _ema_eye: float = 0.0
    _ema_posture: float = 0.0
    _ema_voice: float = 0.0
    _confidence_model: ConfidenceModel = field(default_factory=lambda: ConfidenceModel(DEFAULT_MODEL_PATH))
    _confidence_loaded: bool = False

    def reset(self, mode: str = "practice", language: str = "en") -> None:
        self.pcm16.clear()
        self.last_emit_ms = 0
        self.last_transcribe_ms = 0
        self.last_transcribed_bytes = 0
        self.transcript = ""
        self.eye_contact = 0.0
        self.posture = 0.0
        self.emotion = "neutral"
        self.voice_variation = 0.0
        self.history.clear()
        self._ema_eye = 0.0
        self._ema_posture = 0.0
        self._ema_voice = 0.0
        if not self._confidence_loaded:
            try:
                self._confidence_loaded = self._confidence_model.try_load()
            except Exception:
                self._confidence_loaded = False
        self.language = language or "en"
        created = create_session(language=self.language, mode=mode or "practice")
        self.session_id = created.id

    def ingest_video_metrics(self, payload: dict) -> None:
        try:
            eye = float(payload.get("eye_contact", self.eye_contact))
            post = float(payload.get("posture", self.posture))
            # Smooth visual signals to avoid UI jitter.
            a = 0.25
            self._ema_eye = (1 - a) * self._ema_eye + a * eye
            self._ema_posture = (1 - a) * self._ema_posture + a * post
            self.eye_contact = self._ema_eye
            self.posture = self._ema_posture
            emo = payload.get("emotion")
            if isinstance(emo, str) and emo:
                self.emotion = emo
        except Exception:
            return

    def ingest_audio_pcm16(self, pcm16: bytes, sample_rate_hz: int, now_ms: int) -> List[ServerMessage]:
        if sample_rate_hz != self.sample_rate_hz:
            # Keep a single session SR for now; frontend will send 16k.
            self.sample_rate_hz = sample_rate_hz
        self.pcm16.extend(pcm16)

        out: list[ServerMessage] = []

        # Continuity proxy: ratio of voiced frames in last ~3 seconds.
        tail_ms = 3000
        tail_bytes = int(self.sample_rate_hz * (tail_ms / 1000.0) * 2)
        tail = bytes(self.pcm16[-tail_bytes:]) if len(self.pcm16) > tail_bytes else bytes(self.pcm16)
        continuity = self.audio.vad_speech_ratio(tail, self.sample_rate_hz)

        # Transcribe incrementally every ~2.5 seconds (on speech).
        if self.last_transcribe_ms == 0 or (now_ms - self.last_transcribe_ms) >= 2500:
            if continuity >= 0.15 and len(self.pcm16) > self.last_transcribed_bytes + int(self.sample_rate_hz * 0.5) * 2:
                # Overlap 0.5s to reduce word cut-offs.
                overlap_bytes = int(self.sample_rate_hz * 0.5) * 2
                start = max(0, self.last_transcribed_bytes - overlap_bytes)
                segment_pcm16 = bytes(self.pcm16[start:])
                a = np.frombuffer(segment_pcm16, dtype=np.int16).astype(np.float32) / 32768.0
                try:
                    new_text = self.audio.transcribe_incremental(a, self.sample_rate_hz, self.language)
                except Exception as e:
                    out.append(ServerMessage(type="error", payload={"message": f"stt_failed: {e.__class__.__name__}"}))
                    new_text = ""
                if new_text:
                    new_text = new_text.strip()
                    # Avoid runaway duplication (common with overlapping incremental transcripts).
                    if not self.transcript or not self.transcript.endswith(new_text):
                        self.transcript = (self.transcript + " " + new_text).strip() if self.transcript else new_text
                        out.append(ServerMessage(type="transcript_partial", payload={"text": self.transcript}))
                self.last_transcribed_bytes = len(self.pcm16)
            self.last_transcribe_ms = now_ms

        # Emit realtime metrics update ~1x/sec.
        if self.last_emit_ms == 0 or (now_ms - self.last_emit_ms) >= 1000:
            duration_s = len(self.pcm16) / 2 / float(self.sample_rate_hz)
            t_ms = int(duration_s * 1000)
            # Compute voice variation on recent audio window.
            tail_ms_voice = 2500
            tail_bytes_voice = int(self.sample_rate_hz * (tail_ms_voice / 1000.0) * 2)
            tail_voice = bytes(self.pcm16[-tail_bytes_voice:]) if len(self.pcm16) > tail_bytes_voice else bytes(self.pcm16)
            a_voice = np.frombuffer(tail_voice, dtype=np.int16).astype(np.float32) / 32768.0
            vv = compute_voice_variation(a_voice, self.sample_rate_hz)
            a = 0.2
            self._ema_voice = (1 - a) * self._ema_voice + a * vv
            self.voice_variation = self._ema_voice
            m = self.audio.compute_metrics(self.transcript, t_ms=t_ms, continuity=continuity)
            self.history.append({"t_ms": t_ms, "wpm": m.wpm, "fillers_density": m.fillers_density})
            if len(self.history) > 600:
                self.history = self.history[-600:]

            # Heuristic confidence score (trainable model hooks come later).
            # Penalize fillers + too-fast/slow pace + low continuity.
            pace_pen = 0.0
            if m.wpm < 110:
                pace_pen = min(25.0, (110 - m.wpm) * 0.25)
            elif m.wpm > 170:
                pace_pen = min(25.0, (m.wpm - 170) * 0.25)
            filler_pen = min(35.0, m.fillers_density * 700.0)  # 0.05 -> 35
            cont_pen = min(25.0, (1.0 - m.continuity) * 25.0)
            confidence = float(max(0.0, min(100.0, 100.0 - pace_pen - filler_pen - cont_pen)))
            if self._confidence_loaded:
                try:
                    pred = self._confidence_model.predict_score_0_100(
                        ConfidenceFeatures(
                            wpm=float(m.wpm),
                            fillers_density=float(m.fillers_density),
                            continuity=float(m.continuity),
                            eye_contact=float(self.eye_contact),
                            posture=float(self.posture),
                            voice_variation=float(self.voice_variation),
                        )
                    )
                    if pred is not None:
                        confidence = float(max(0.0, min(100.0, pred)))
                except Exception:
                    pass

            out.append(
                ServerMessage(
                    type="realtime_metrics",
                    payload={
                        "t_ms": t_ms,
                        "wpm": round(m.wpm, 1),
                        "wpm_label": m.wpm_label,
                        "fillers_total": m.fillers_total,
                        "fillers_density": round(m.fillers_density, 4),
                        "fillers_by_type": m.fillers_by_type,
                        "continuity": round(m.continuity, 3),
                        "confidence": round(confidence, 1),
                        "confidence_label": (
                            "beginner"
                            if confidence < 55
                            else "average"
                            if confidence < 70
                            else "good"
                            if confidence < 85
                            else "excellent"
                        ),
                        "suggestions": suggestions_for(m.wpm, m.fillers_density, m.continuity),
                        "insights": generate_insights(self.history, m.fillers_by_type),
                        "emotion": self.emotion,
                        "eye_contact": round(float(self.eye_contact), 3),
                        "posture": round(float(self.posture), 3),
                        "voice_variation": round(float(self.voice_variation), 3),
                    },
                )
            )
            if self.session_id is not None:
                add_metric_point(self.session_id, out[-1].payload)
            self.last_emit_ms = now_ms

        return out

    def finalize(self) -> dict:
        summary = {
            "transcript_len": len(self.transcript),
            "last_metrics": self.history[-1] if self.history else None,
        }
        if self.session_id is not None:
            finalize_session(self.session_id, transcript=self.transcript, summary=summary)
        return {"session_id": self.session_id, "transcript": self.transcript}

    def _pcm16_to_wav_bytes(self) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate_hz)
            wf.writeframes(bytes(self.pcm16))
        return buf.getvalue()

    def _pcm16_to_float32(self) -> np.ndarray:
        a = np.frombuffer(bytes(self.pcm16), dtype=np.int16).astype(np.float32)
        return a / 32768.0

