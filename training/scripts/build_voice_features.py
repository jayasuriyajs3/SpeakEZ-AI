from __future__ import annotations

import csv
from pathlib import Path

import librosa
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
META_PATH = ROOT / "training" / "datasets" / "voice" / "metadata_template.csv"
OUT_PATH = ROOT / "training" / "datasets" / "voice" / "voice_features.csv"


def extract_features(path: Path, sr: int = 16000) -> dict:
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    f0 = librosa.yin(y, fmin=80, fmax=320, sr=sr)
    f0 = f0[np.isfinite(f0)]
    pitch_var = float(np.std(f0) / max(1e-6, np.mean(f0))) if f0.size else 0.0

    rms = librosa.feature.rms(y=y)[0]
    energy_var = float(np.std(rms) / max(1e-6, np.mean(rms))) if rms.size else 0.0

    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    centroid_var = float(np.std(centroid) / max(1e-6, np.mean(centroid))) if centroid.size else 0.0

    return {
        "pitch_var": pitch_var,
        "energy_var": energy_var,
        "centroid_var": centroid_var,
    }


def main() -> None:
    if not META_PATH.exists():
        raise FileNotFoundError(f"Missing metadata file: {META_PATH}")

    rows_out: list[dict] = []
    with META_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            audio_path = Path(row.get("audio_path", "").strip())
            label = row.get("label", "").strip().lower()
            if not audio_path or not label:
                continue
            full_path = (ROOT / audio_path) if not audio_path.is_absolute() else audio_path
            if not full_path.exists():
                print(f"Skip missing file: {full_path}")
                continue
            feats = extract_features(full_path)
            rows_out.append(
                {
                    "audio_path": str(audio_path).replace("\\", "/"),
                    "label": label,
                    **feats,
                }
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["audio_path", "label", "pitch_var", "energy_var", "centroid_var"])
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Exported {len(rows_out)} rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
