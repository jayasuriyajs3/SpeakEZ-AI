from __future__ import annotations

import re


def score_content(answer: str) -> float:
    """
    Very lightweight rubric score 0..100.
    This is designed to be replaceable by an LLM rubric later.
    """
    a = (answer or "").strip()
    if not a:
        return 0.0

    words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ']+", a)
    wc = len(words)
    length_score = 0.0
    if wc < 25:
        length_score = 30.0
    elif wc < 60:
        length_score = 65.0
    else:
        length_score = 80.0

    # Structure proxy: presence of connectors.
    connectors = ["because", "so", "therefore", "however", "for example", "as a result", "then"]
    structure = sum(1 for c in connectors if c in a.lower())
    structure_score = min(20.0, structure * 5.0)

    # Specificity proxy: numbers/metrics and named nouns (rough).
    numbers = len(re.findall(r"\b\d+%?\b", a))
    specificity_score = min(20.0, numbers * 6.0)

    return max(0.0, min(100.0, length_score + structure_score + specificity_score))


def score_overall(content: float, confidence: float) -> float:
    return max(0.0, min(100.0, 0.55 * content + 0.45 * confidence))

