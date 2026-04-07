from __future__ import annotations

import numpy as np
import librosa


def compute_voice_variation(audio_f32: np.ndarray, sample_rate_hz: int) -> float:
    """
    Returns a 0..1 proxy for expressiveness based on pitch variation.
    - 0 ~ very monotone / unvoiced
    - 1 ~ high variation
    """
    if audio_f32.size < sample_rate_hz // 2:
        return 0.0

    y = audio_f32.astype(np.float32)
    # Limit to recent window for realtime
    max_len = int(sample_rate_hz * 2.5)
    if y.size > max_len:
        y = y[-max_len:]

    try:
        f0 = librosa.yin(y, fmin=80, fmax=320, sr=sample_rate_hz)
    except Exception:
        return 0.0

    f0 = np.asarray(f0)
    f0 = f0[np.isfinite(f0)]
    if f0.size < 5:
        return 0.0

    mean = float(np.mean(f0))
    std = float(np.std(f0))
    if mean <= 1e-6:
        return 0.0

    rel = std / mean  # ~0.03 monotone, 0.08 expressive (roughly)
    return float(max(0.0, min(1.0, (rel - 0.02) / 0.10)))

