from __future__ import annotations

from typing import Any

CLAIM_SAFETY = "NO_TRUTH_UNTIL_ACTIVE_MATCH_VALIDATION"

DEPENDENCY_RISK_FLAGS = {
    "external_python_pkg",
    "tracking_required",
    "video_required",
    "manual_review_required",
}

ENGINE_VALUE = {
    "canonical_ingest": 18,
    "data_quality_gate": 18,
    "sequence_engine": 16,
    "metric_fusion": 15,
    "pattern_discovery": 14,
    "behaviour_graph": 13,
    "momentum_engine": 12,
    "opportunity_failure": 12,
    "explanation_engine": 10,
    "unknown": 0,
}

REVIEW_TERMS = {
    "truth",
    "control",
    "intent",
    "body",
    "tracking",
    "video",
}


def _member_text(member: dict[str, Any]) -> str:
    parts = [
        str(member.get("file_name", "")),
        str(member.get("normalized_name", "")),
        str(member.get("source_path", "")),
        " ".join(map(str, member.get("symbols", []) or [])),
    ]
    return " ".join(parts).lower()


def _review_flags(candidate: dict[str, Any]) -> list[str]:
    flags: set[str] = set()
    for member in candidate.get("members", []) or []:
        text = _member_text(member)
        for term in REVIEW_TERMS:
            if term in text:
                flags.add(f"review_term:{term}")
        for flag in member.get("dependency_flags", []) or []:
            if str(flag) in DEPENDENCY_RISK_FLAGS:
                flags.add(f"dependency:{flag}")
    return sorted(flags)


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    capability = str(candidate.get("dominant_capability", "unknown"))
    source_count = int(candidate.get("source_count", 0) or 0)
    sources = set(candidate.get("sources", []) or [])
    members = candidate.get("members", []) or []
    flags = _review_flags(candidate)

    score = 0
    score += ENGINE_VALUE.get(capability, 0)
    score += min(source_count, 5) * 2
    score += min(len(sources), 5) * 2
    if members:
        score += 4
    if capability == "unknown":
        score -= 12
    if flags:
        score -= 8
    if not candidate.get("active_match_validation_required", True):
        score -= 20

    score = max(0, min(100, score))

    if not candidate.get("active_match_validation_required", True):
        band = "BLOCKED"
        action = "block_candidate"
    elif flags:
        band = "BOUNDARY_REVIEW"
        action = "review_boundary"
    elif score >= 28:
        band = "ADAPT_READY"
        action = "adapt_candidate"
    elif score >= 18:
        band = "BOUNDARY_REVIEW"
        action = "review_boundary"
    else:
        band = "REFERENCE_ONLY"
        action = "keep_reference_only"

    return {
        "composite_id": candidate.get("composite_id", "UNKNOWN"),
        "readiness_score": score,
        "readiness_band": band,
        "risk_flags": flags,
        "recommended_action": action,
        "claim_safety": CLAIM_SAFETY,
        "active_match_validation_required": True,
    }


def score_registry(registry: dict[str, Any]) -> dict[str, Any]:
    scores = [score_candidate(c) for c in registry.get("composites", [])]
    scores.sort(key=lambda row: row["readiness_score"], reverse=True)
    return {
        "registry_id": "boundary_analysis_score_registry_v1",
        "status": "PASS",
        "score_count": len(scores),
        "claim_safety": CLAIM_SAFETY,
        "active_match_validation_required": True,
        "scores": scores,
    }
