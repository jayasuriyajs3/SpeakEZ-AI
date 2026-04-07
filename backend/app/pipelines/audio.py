from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import webrtcvad
from faster_whisper import WhisperModel

from app.settings import settings


FILLERS = ["um", "uh", "like", "you know", "actually", "basically", "so"]
FILLER_PATTERNS = [rf"\b{re.escape(f)}\b" for f in FILLERS]


def tokenize_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", text.lower())


def count_fillers(tokens: Iterable[str]) -> int:
    text = " ".join(tokens)
    total = 0
    for pat in FILLER_PATTERNS:
        total += len(re.findall(pat, text, flags=re.IGNORECASE))
    return total


def filler_breakdown(tokens: Iterable[str]) -> dict[str, int]:
    text = " ".join(tokens)
    out: dict[str, int] = {}
    for f, pat in zip(FILLERS, FILLER_PATTERNS, strict=True):
        out[f] = len(re.findall(pat, text, flags=re.IGNORECASE))
    return out


def classify_wpm(wpm: float) -> str:
    if wpm < 110:
        return "slow"
    if wpm <= 170:
        return "optimal"
    return "fast"


def suggestions_for(wpm: float, filler_density: float, continuity: float) -> list[str]:
    sug: list[str] = []
    if filler_density >= 0.05:
        sug.append("Reduce filler usage (try pausing instead of saying ‘um/uh/like’).")
    if wpm < 110:
        sug.append("Increase pace slightly to sound more confident.")
    elif wpm > 170:
        sug.append("Slow down a bit for clarity—aim for a steady pace.")
    if continuity < 0.55:
        sug.append("Try to speak in complete thoughts—avoid frequent stops mid-sentence.")
    if not sug:
        sug.append("Good consistency—keep your pace steady and keep sentences crisp.")
    return sug


@dataclass
class AudioMetrics:
    t_ms: int
    wpm: float
    wpm_label: str
    fillers_total: int
    fillers_density: float
    fillers_by_type: dict[str, int]
    continuity: float


class AudioPipeline:
    def __init__(self) -> None:
        self._vad = webrtcvad.Vad(2)
        self._model: WhisperModel | None = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            if settings.whisper_device == "auto":
                self._model = WhisperModel(settings.whisper_model, compute_type="int8")
            else:
                self._model = WhisperModel(settings.whisper_model, device=settings.whisper_device, compute_type="int8")
        return self._model

    def vad_speech_ratio(self, pcm16: bytes, sample_rate_hz: int) -> float:
        # WebRTC VAD only supports 8/16/32/48k.
        if sample_rate_hz not in (8000, 16000, 32000, 48000):
            return 0.0

        frame_ms = 30
        frame_bytes = int(sample_rate_hz * (frame_ms / 1000.0) * 2)
        if len(pcm16) < frame_bytes:
            return 0.0

        speech = 0
        total = 0
        for i in range(0, len(pcm16) - frame_bytes + 1, frame_bytes):
            frame = pcm16[i : i + frame_bytes]
            total += 1
            if self._vad.is_speech(frame, sample_rate_hz):
                speech += 1
        return float(speech) / float(total) if total else 0.0

    def transcribe_incremental(
        self,
        audio_f32: np.ndarray,
        sample_rate_hz: int,
        language: str | None,
    ) -> str:
        model = self._get_model()
        audio = np.ascontiguousarray(audio_f32, dtype=np.float32)
        if audio.size < max(1024, int(sample_rate_hz * 0.75)):
            return ""

        attempts = (
            {"vad_filter": True, "vad_parameters": {"min_silence_duration_ms": 250}},
            {"vad_filter": False},
        )

        last_error: Exception | None = None
        for attempt in attempts:
            try:
                segments, _info = model.transcribe(
                    audio,
                    language=language,
                    condition_on_previous_text=False,
                    beam_size=1,
                    **attempt,
                )
                parts: list[str] = []
                for s in segments:
                    if s.text:
                        parts.append(s.text.strip())
                return " ".join(parts).strip()
            except Exception as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        return ""

    def compute_metrics(self, transcript: str, t_ms: int, continuity: float) -> AudioMetrics:
        tokens = tokenize_words(transcript)
        words = len(tokens)
        minutes = max(1e-6, t_ms / 60000.0)
        wpm = words / minutes
        fillers = count_fillers(tokens)
        fillers_by_type = filler_breakdown(tokens)
        density = (fillers / max(1, words)) if words else 0.0
        return AudioMetrics(
            t_ms=t_ms,
            wpm=float(wpm),
            wpm_label=classify_wpm(float(wpm)),
            fillers_total=int(fillers),
            fillers_density=float(density),
            fillers_by_type=fillers_by_type,
            continuity=float(continuity),
        )

