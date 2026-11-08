"""Scoring engine (FR-10, FR-14, FR-15) with the midterm defects fixed.

D1  a missing assessment is NOT ASSESSED (None) and is excluded, not counted as zero
D2  equal scores share the same rank
D3  a policy whose weights sum to zero (or contain negatives) is rejected
Scores are stored unrounded; rounding happens only for display (NFR-08 repeatability).
"""
from typing import Mapping

COMPONENTS = ("tech", "exp", "edu", "soft", "ver")  # same five factors as the prototype
DEFAULT_WEIGHTS = {"tech": 35, "exp": 25, "edu": 20, "soft": 10, "ver": 10}


class PolicyError(ValueError):
    pass


def validate_weights(weights: Mapping[str, float]) -> dict:
    unknown = set(weights) - set(COMPONENTS)
    if unknown:
        raise PolicyError(f"Unknown weight(s): {sorted(unknown)}")
    w = {k: float(weights.get(k, 0)) for k in COMPONENTS}
    if any(v < 0 for v in w.values()):
        raise PolicyError("Weights cannot be negative")
    if sum(w.values()) <= 0:
        raise PolicyError("Weights must add up to more than zero")  # D3
    return w


def compute_score(components: Mapping[str, float | None], weights: Mapping[str, float]) -> dict:
    """Weighted mean over the components that have evidence.

    Returns score (unrounded, 0-100), the components used, the ones NOT ASSESSED, and
    complete=True only when every positively weighted component has evidence (FR-14).
    """
    w = validate_weights(weights)
    used, missing = {}, []
    for k in COMPONENTS:
        if w[k] == 0:
            continue
        v = components.get(k)
        if v is None:
            missing.append(k)  # D1: excluded, not zero
            continue
        v = float(v)
        if not 0 <= v <= 100:
            raise ValueError(f"Component {k} must be between 0 and 100")
        used[k] = v
    total = sum(w[k] for k in used)
    score = sum(used[k] * w[k] for k in used) / total if total else None
    return {"score": score, "used": used, "not_assessed": missing, "complete": not missing}


def rank(scores: Mapping[int, float]) -> dict[int, int]:
    """Competition ranking (1, 2, 2, 4): equal scores share a rank (D2)."""
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ranks, prev, prev_rank = {}, None, 0
    for i, (key, s) in enumerate(ordered, start=1):
        if prev is None or s != prev:
            prev_rank = i
        ranks[key] = prev_rank
        prev = s
    return ranks
