from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score


ROOT = Path(__file__).resolve().parents[2]

CONF_OUT = ROOT / "training" / "datasets" / "confidence" / "confidence_synthetic_15000.csv"
VOICE_OUT = ROOT / "training" / "datasets" / "voice" / "voice_features_10000.csv"
EMOTION_OUT = ROOT / "training" / "datasets" / "emotion" / "emotion_synthetic_20000.csv"

BACKEND_CONF_MODEL = ROOT / "backend" / "models" / "confidence_model.joblib"
BACKEND_CONF_CARD = ROOT / "backend" / "models" / "confidence_model_card.json"
VOICE_MODEL = ROOT / "training" / "models" / "voice_modulation_model.joblib"
EMOTION_MODEL = ROOT / "training" / "models" / "emotion_baseline_model.joblib"


def _write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def generate_confidence(n_per_class: int = 5000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    labels = ["poor", "average", "good"]
    rows: list[dict] = []
    X: list[list[float]] = []
    y: list[str] = []

    for label in labels:
        for _ in range(n_per_class):
            if label == "poor":
                wpm = float(rng.normal(95, 15))
                fillers_density = float(np.clip(rng.normal(0.09, 0.03), 0.0, 0.25))
                continuity = float(np.clip(rng.normal(0.45, 0.18), 0.0, 1.0))
                eye_contact = float(np.clip(rng.normal(0.35, 0.2), 0.0, 1.0))
                posture = float(np.clip(rng.normal(0.4, 0.2), 0.0, 1.0))
                voice_variation = float(np.clip(rng.normal(0.2, 0.15), 0.0, 1.0))
            elif label == "average":
                wpm = float(rng.normal(130, 18))
                fillers_density = float(np.clip(rng.normal(0.045, 0.02), 0.0, 0.2))
                continuity = float(np.clip(rng.normal(0.7, 0.15), 0.0, 1.0))
                eye_contact = float(np.clip(rng.normal(0.6, 0.18), 0.0, 1.0))
                posture = float(np.clip(rng.normal(0.62, 0.16), 0.0, 1.0))
                voice_variation = float(np.clip(rng.normal(0.45, 0.18), 0.0, 1.0))
            else:
                wpm = float(rng.normal(150, 15))
                fillers_density = float(np.clip(rng.normal(0.015, 0.012), 0.0, 0.1))
                continuity = float(np.clip(rng.normal(0.88, 0.09), 0.0, 1.0))
                eye_contact = float(np.clip(rng.normal(0.8, 0.12), 0.0, 1.0))
                posture = float(np.clip(rng.normal(0.82, 0.1), 0.0, 1.0))
                voice_variation = float(np.clip(rng.normal(0.7, 0.12), 0.0, 1.0))

            row = {
                "label_confidence": label,
                "wpm": round(wpm, 4),
                "fillers_density": round(fillers_density, 6),
                "continuity": round(continuity, 6),
                "eye_contact": round(eye_contact, 6),
                "posture": round(posture, 6),
                "voice_variation": round(voice_variation, 6),
            }
            rows.append(row)
            X.append([wpm, fillers_density, continuity, eye_contact, posture, voice_variation])
            y.append(label)

    _write_csv(
        CONF_OUT,
        [
            "label_confidence",
            "wpm",
            "fillers_density",
            "continuity",
            "eye_contact",
            "posture",
            "voice_variation",
        ],
        rows,
    )
    return np.array(X, dtype=np.float32), np.array(y)


def generate_voice(n_per_class: int = 5000, seed: int = 43) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    labels = ["monotone", "expressive"]
    rows: list[dict] = []
    X: list[list[float]] = []
    y: list[str] = []

    for label in labels:
        for i in range(n_per_class):
            if label == "monotone":
                pitch_var = float(np.clip(rng.normal(0.03, 0.015), 0.0, 0.2))
                energy_var = float(np.clip(rng.normal(0.08, 0.04), 0.0, 0.4))
                centroid_var = float(np.clip(rng.normal(0.06, 0.03), 0.0, 0.4))
            else:
                pitch_var = float(np.clip(rng.normal(0.12, 0.035), 0.0, 0.4))
                energy_var = float(np.clip(rng.normal(0.2, 0.07), 0.0, 0.6))
                centroid_var = float(np.clip(rng.normal(0.18, 0.06), 0.0, 0.6))

            row = {
                "audio_path": f"synthetic/{label}_{i:05d}.wav",
                "label": label,
                "pitch_var": round(pitch_var, 6),
                "energy_var": round(energy_var, 6),
                "centroid_var": round(centroid_var, 6),
            }
            rows.append(row)
            X.append([pitch_var, energy_var, centroid_var])
            y.append(label)

    _write_csv(VOICE_OUT, ["audio_path", "label", "pitch_var", "energy_var", "centroid_var"], rows)
    return np.array(X, dtype=np.float32), np.array(y)


def generate_emotion(n_per_class: int = 5000, seed: int = 44) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    labels = ["happy", "neutral", "nervous", "stressed"]
    rows: list[dict] = []
    X: list[list[float]] = []
    y: list[str] = []

    for label in labels:
        for _ in range(n_per_class):
            if label == "happy":
                smile = float(np.clip(rng.normal(0.75, 0.12), 0.0, 1.0))
                brow_tension = float(np.clip(rng.normal(0.2, 0.1), 0.0, 1.0))
                jaw_open = float(np.clip(rng.normal(0.35, 0.12), 0.0, 1.0))
                eye_open = float(np.clip(rng.normal(0.7, 0.14), 0.0, 1.0))
            elif label == "neutral":
                smile = float(np.clip(rng.normal(0.25, 0.1), 0.0, 1.0))
                brow_tension = float(np.clip(rng.normal(0.3, 0.12), 0.0, 1.0))
                jaw_open = float(np.clip(rng.normal(0.25, 0.1), 0.0, 1.0))
                eye_open = float(np.clip(rng.normal(0.55, 0.12), 0.0, 1.0))
            elif label == "nervous":
                smile = float(np.clip(rng.normal(0.18, 0.08), 0.0, 1.0))
                brow_tension = float(np.clip(rng.normal(0.55, 0.14), 0.0, 1.0))
                jaw_open = float(np.clip(rng.normal(0.62, 0.16), 0.0, 1.0))
                eye_open = float(np.clip(rng.normal(0.52, 0.14), 0.0, 1.0))
            else:
                smile = float(np.clip(rng.normal(0.1, 0.06), 0.0, 1.0))
                brow_tension = float(np.clip(rng.normal(0.78, 0.12), 0.0, 1.0))
                jaw_open = float(np.clip(rng.normal(0.55, 0.15), 0.0, 1.0))
                eye_open = float(np.clip(rng.normal(0.45, 0.13), 0.0, 1.0))

            rows.append(
                {
                    "label": label,
                    "smile": round(smile, 6),
                    "brow_tension": round(brow_tension, 6),
                    "jaw_open": round(jaw_open, 6),
                    "eye_open": round(eye_open, 6),
                }
            )
            X.append([smile, brow_tension, jaw_open, eye_open])
            y.append(label)

    _write_csv(EMOTION_OUT, ["label", "smile", "brow_tension", "jaw_open", "eye_open"], rows)
    return np.array(X, dtype=np.float32), np.array(y)


def fit_and_save_model(X: np.ndarray, y: np.ndarray, out_path: Path, title: str) -> dict:
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=7,
        stratify=y,
    )
    clf = RandomForestClassifier(n_estimators=280, max_depth=16, random_state=7, n_jobs=-1)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)
    acc = float(accuracy_score(y_test, preds))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out_path)
    report = classification_report(y_test, preds, output_dict=True)
    return {"accuracy": acc, "report": report, "rows": int(len(X))}


def main() -> None:
    print("Generating synthetic datasets with ~5000 rows per class...")

    Xc, yc = generate_confidence(5000)
    Xv, yv = generate_voice(5000)
    Xe, ye = generate_emotion(5000)

    conf_stats = fit_and_save_model(Xc, yc, BACKEND_CONF_MODEL, "confidence")
    voice_stats = fit_and_save_model(Xv, yv, VOICE_MODEL, "voice")
    emo_stats = fit_and_save_model(Xe, ye, EMOTION_MODEL, "emotion")

    model_card = {
        "model": "confidence_model.joblib",
        "source": str(CONF_OUT.relative_to(ROOT)).replace("\\", "/"),
        "rows": conf_stats["rows"],
        "labels": ["poor", "average", "good"],
        "accuracy": conf_stats["accuracy"],
        "note": "Synthetic bootstrap dataset; replace/augment with real labeled sessions for production quality.",
    }
    BACKEND_CONF_CARD.write_text(json.dumps(model_card, indent=2), encoding="utf-8")

    print("Done.")
    print(f"Confidence dataset: {CONF_OUT}")
    print(f"Voice dataset: {VOICE_OUT}")
    print(f"Emotion dataset: {EMOTION_OUT}")
    print(f"Saved backend confidence model: {BACKEND_CONF_MODEL}")
    print(f"Saved voice model: {VOICE_MODEL}")
    print(f"Saved emotion model: {EMOTION_MODEL}")


if __name__ == "__main__":
    main()
