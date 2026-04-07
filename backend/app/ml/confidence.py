from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib


@dataclass
class ConfidenceFeatures:
    wpm: float
    fillers_density: float
    continuity: float
    eye_contact: float
    posture: float
    voice_variation: float


class ConfidenceModel:
    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        self._model = None

    def try_load(self) -> bool:
        p = Path(self.model_path)
        if not p.exists():
            return False
        self._model = joblib.load(p)
        return True

    def predict_score_0_100(self, f: ConfidenceFeatures) -> Optional[float]:
        if self._model is None:
            return None
        X = [[f.wpm, f.fillers_density, f.continuity, f.eye_contact, f.posture, f.voice_variation]]
        # supports either regression (0..1 or 0..100) or classification probabilities
        if hasattr(self._model, "predict_proba"):
            proba = self._model.predict_proba(X)[0]
            # assume classes ordered poor/average/good
            # map to 0..100 with weights
            weights = [20, 60, 90][: len(proba)]
            return float(sum(p * w for p, w in zip(proba, weights, strict=False)))
        y = float(self._model.predict(X)[0])
        if y <= 1.0:
            return y * 100.0
        return max(0.0, min(100.0, y))


DEFAULT_MODEL_PATH = str(Path(__file__).resolve().parents[2] / "models" / "confidence_model.joblib")

