"""Historical Video Intelligence Lite V1 — shared contract vocabulary.

Video-derived rows are DERIVED_OBSERVATION candidates. A row becomes verified
only through an independent reference label or an explicit human review
decision. Nothing in this module promotes a detector score to event truth.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

MODULE_ID = "historical_video_intelligence_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "VIDEO_DERIVED_EVENT_CANDIDATE_ONLY"

# Event families in scope. Only these are ever emitted by detectors.
EVENT_TYPES = (
    "SHOT",
    "GOAL",
    "SET_PIECE_RESTART",
    "FREE_KICK",
    "CORNER_KICK",
    "THROW_IN",
    "KICK_OFF",
    "BALL_RECOVERY",
)

# Capability states. SUPPORTED is granted only by a validation report.
SUPPORTED = "SUPPORTED_IN_VALIDATED_DOMAIN"
EXPERIMENTAL = "EXPERIMENTAL"
NOT_SUPPORTED = "NOT_SUPPORTED"
CAPABILITY_STATES = (SUPPORTED, EXPERIMENTAL, NOT_SUPPORTED)

# Default capability before any validation evidence exists.
DEFAULT_CAPABILITY = {event_type: NOT_SUPPORTED for event_type in EVENT_TYPES}

CANDIDATE = "CANDIDATE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
VERIFIED_REFERENCE = "VERIFIED_REFERENCE"
VERIFIED_HUMAN = "VERIFIED_HUMAN"
REJECTED = "REJECTED"
VERIFIED_STATES = (VERIFIED_REFERENCE, VERIFIED_HUMAN)
VERIFICATION_STATES = (CANDIDATE, REVIEW_REQUIRED, VERIFIED_REFERENCE, VERIFIED_HUMAN, REJECTED)

EVIDENCE_KINDS = (
    "DIRECT_OBSERVATION",
    "DERIVED_OBSERVATION",
    "REFERENCE_LABEL",
    "HUMAN_REVIEW",
    "MODEL_OUTPUT",
)

OBSERVED_LAYER = "OBSERVED_VIDEO_LAYER"
COUNTERFACTUAL_LAYER = "COUNTERFACTUAL_MODEL_LAYER"

UNKNOWN = "UNKNOWN"

# HPFA CSV surface mapping. `csv_surface_reader_lite` maps `SET PIECE` +
# subtype into restart families and `SHOT` / `RECOVERY` into action families.
HPFA_CSV_EVENT_TYPE = {
    "SHOT": ("SHOT", ""),
    "GOAL": ("GOAL", ""),
    "SET_PIECE_RESTART": ("SET PIECE", "UNKNOWN"),
    "FREE_KICK": ("SET PIECE", "FREE KICK"),
    "CORNER_KICK": ("SET PIECE", "CORNER KICK"),
    "THROW_IN": ("SET PIECE", "THROW IN"),
    "KICK_OFF": ("SET PIECE", "KICK OFF"),
    "BALL_RECOVERY": ("RECOVERY", ""),
}

CLAIM_BOUNDARY = {
    "canonical_event_count": CANONICAL_EVENT_COUNT,
    "tracking_data_available": False,
    "tracking_statistics_emitted": False,
    "validated_team_identity": False,
    "validated_player_identity": False,
    "detector_score_is_probability": False,
    "domain_transfer_admitted": False,
    "counterfactual_mixed_with_observation": False,
    "production_release": False,
}

DOES_NOT_MEASURE = (
    "tracking_statistics",
    "distance_covered",
    "speed_or_physical_load",
    "pitch_control",
    "team_shape_or_compactness",
    "pressing_intensity",
    "possession_share",
    "pass_network",
    "tactical_intention",
    "causal_effect",
)

# Required event row fields (JSON contract). CSV export is a projection.
EVENT_FIELDS = (
    "event_id",
    "layer",
    "source_video_id",
    "source_fingerprint",
    "rights_manifest_id",
    "period",
    "video_time_s",
    "video_time_end_s",
    "video_timestamp",
    "time_uncertainty_s",
    "match_clock",
    "event_type",
    "event_subtype",
    "team",
    "team_basis",
    "player",
    "player_basis",
    "detector_id",
    "stage",
    "score",
    "score_basis",
    "confidence_bound",
    "evidence_kind",
    "verification_status",
    "verification_basis",
    "capability_status",
    "claim_ceiling",
)


def video_timestamp(seconds: float) -> str:
    if seconds is None or not math.isfinite(seconds) or seconds < 0:
        return UNKNOWN
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def event_id(source_fingerprint: str, event_type: str, video_time_s: float, detector_id: str) -> str:
    material = f"{source_fingerprint}|{event_type}|{video_time_s:.3f}|{detector_id}"
    return "hvi_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def wilson_interval(successes: int, total: int, z: float = 1.959964) -> tuple[float, float] | None:
    if total <= 0:
        return None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def make_event(
    *,
    source_video_id: str,
    source_fingerprint: str,
    rights_manifest_id: str,
    event_type: str,
    video_time_s: float,
    detector_id: str,
    stage: str,
    score: float,
    time_uncertainty_s: float,
    period: str = UNKNOWN,
    video_time_end_s: float | None = None,
    event_subtype: str = UNKNOWN,
    capability_status: str = NOT_SUPPORTED,
    features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown_event_type:{event_type}")
    if capability_status not in CAPABILITY_STATES:
        raise ValueError(f"unknown_capability_status:{capability_status}")
    return {
        "event_id": event_id(source_fingerprint, event_type, video_time_s, detector_id),
        "layer": OBSERVED_LAYER,
        "source_video_id": source_video_id,
        "source_fingerprint": source_fingerprint,
        "rights_manifest_id": rights_manifest_id,
        "period": period,
        "video_time_s": round(float(video_time_s), 3),
        "video_time_end_s": None if video_time_end_s is None else round(float(video_time_end_s), 3),
        "video_timestamp": video_timestamp(video_time_s),
        "time_uncertainty_s": round(float(time_uncertainty_s), 3),
        "match_clock": UNKNOWN,
        "event_type": event_type,
        "event_subtype": event_subtype,
        "team": UNKNOWN,
        "team_basis": "NOT_OBSERVED",
        "player": UNKNOWN,
        "player_basis": "NOT_RECOGNISED",
        "detector_id": detector_id,
        "stage": stage,
        "score": round(float(score), 4),
        "score_basis": "UNCALIBRATED_DETECTOR_SCORE_NOT_PROBABILITY",
        "confidence_bound": None,
        "evidence_kind": "DERIVED_OBSERVATION",
        "verification_status": CANDIDATE,
        "verification_basis": None,
        "capability_status": capability_status,
        "claim_ceiling": CLAIM_CEILING,
        "features": features or {},
    }


def validate_event(row: dict[str, Any]) -> list[str]:
    """Return contract violations for one observed-layer event row."""
    problems: list[str] = []
    for field in EVENT_FIELDS:
        if field not in row:
            problems.append(f"missing_field:{field}")
    if row.get("layer") != OBSERVED_LAYER:
        problems.append("non_observed_layer_row")
    if row.get("event_type") not in EVENT_TYPES:
        problems.append("unknown_event_type")
    if row.get("verification_status") not in VERIFICATION_STATES:
        problems.append("unknown_verification_status")
    if row.get("capability_status") not in CAPABILITY_STATES:
        problems.append("unknown_capability_status")
    if row.get("verification_status") in VERIFIED_STATES and not row.get("verification_basis"):
        problems.append("verified_without_basis")
    if row.get("team") not in (None, UNKNOWN) and row.get("team_basis") in (None, "NOT_OBSERVED"):
        problems.append("team_without_basis")
    if row.get("player") not in (None, UNKNOWN) and row.get("player_basis") in (None, "NOT_RECOGNISED"):
        problems.append("player_without_basis")
    time_s = row.get("video_time_s")
    if not isinstance(time_s, (int, float)) or not math.isfinite(time_s) or time_s < 0:
        problems.append("invalid_video_time")
    for key in row:
        if key.startswith("tracking_") or key in {"distance_m", "speed_kmh", "pitch_control"}:
            problems.append(f"tracking_field_forbidden:{key}")
    return problems
