from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT / "training" / "student_samples" / "derived_confidence_samples.csv"
DB_PATH = ROOT / "backend" / "speakez.sqlite"


def read_rows_sqlite() -> Iterable[dict]:
    if not DB_PATH.exists():
        return []

    q = """
    SELECT
      s.id AS session_id,
      s.language AS language,
      s.transcript AS transcript,
      m.wpm AS wpm,
      m.fillers_total AS fillers_total,
      m.fillers_density AS fillers_density,
      m.voice_variation AS voice_variation,
      m.eye_contact AS eye_contact,
      m.posture AS posture,
      m.confidence AS confidence
    FROM Session s
    LEFT JOIN MetricPoint m ON m.id = (
      SELECT id
      FROM MetricPoint
      WHERE session_id = s.id
      ORDER BY t_ms DESC
      LIMIT 1
    )
    WHERE s.ended_at IS NOT NULL
    ORDER BY s.started_at DESC
    """

    with sqlite3.connect(DB_PATH) as conn:
      conn.row_factory = sqlite3.Row
      rows = conn.execute(q).fetchall()

    out: list[dict] = []
    for r in rows:
      transcript = (r["transcript"] or "").strip()
      out.append(
        {
          "session_id": r["session_id"],
          "language": r["language"] or "en",
          "label_confidence": "",  # Fill manually: poor|average|good
          "label_notes": "",
          "fillers_total": int(r["fillers_total"] or 0),
          "fillers_density": float(r["fillers_density"] or 0.0),
          "wpm": float(r["wpm"] or 0.0),
          "voice_variation": float(r["voice_variation"] or 0.0),
          "eye_contact": float(r["eye_contact"] or 0.0),
          "posture": float(r["posture"] or 0.0),
          "confidence_auto": float(r["confidence"] or 0.0),
          "transcript_len": len(transcript),
        }
      )
    return out


def main() -> None:
    rows = list(read_rows_sqlite())
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    cols = [
      "session_id",
      "language",
      "label_confidence",
      "label_notes",
      "fillers_total",
      "fillers_density",
      "wpm",
      "voice_variation",
      "eye_contact",
      "posture",
      "confidence_auto",
      "transcript_len",
    ]

    with OUT_PATH.open("w", encoding="utf-8", newline="") as f:
      w = csv.DictWriter(f, fieldnames=cols)
      w.writeheader()
      w.writerows(rows)

    print(f"Exported {len(rows)} rows -> {OUT_PATH}")
    print("Next: fill label_confidence as poor|average|good and use this CSV for training.")


if __name__ == "__main__":
    main()
