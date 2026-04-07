from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InsightState:
    last_insights: list[str]


def generate_insights(history: list[dict], fillers_by_type: dict[str, int]) -> list[str]:
    """
    Personalized insight rules based on trends.
    history items should contain: t_ms, wpm, fillers_density.
    """
    if not history:
        return []

    insights: list[str] = []

    # Rule: speed-up after 2 minutes.
    two_min = [h for h in history if h.get("t_ms", 0) >= 120_000]
    if two_min:
        early = history[max(0, len(history) // 4 - 1)]  # ~early reference
        late = two_min[-1]
        if late.get("wpm", 0) - early.get("wpm", 0) > 25:
            insights.append("You tend to speak faster after about 2 minutes—try a deliberate pause between points.")

    # Rule: persistent filler density.
    last = history[-1]
    if last.get("fillers_density", 0) >= 0.05:
        top = sorted(fillers_by_type.items(), key=lambda kv: kv[1], reverse=True)
        top_f = top[0][0] if top and top[0][1] > 0 else "fillers"
        insights.append(f"You overuse “{top_f}”. Replace it with a short pause to sound more confident.")

    # Rule: very slow pace.
    if last.get("wpm", 0) < 105 and last.get("t_ms", 0) > 30_000:
        insights.append("Your pace is a bit slow—try slightly shorter sentences and stronger sentence endings.")

    return insights[:3]

