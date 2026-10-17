"""Reference labels, candidate↔label matching and capability admission.

Reference labels are an independent evidence surface (human annotation). The
detector never reads them; they are used only after detection to measure and
to mark VERIFIED_REFERENCE rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hvi_contract import (
    EVENT_TYPES,
    EXPERIMENTAL,
    NOT_SUPPORTED,
    SUPPORTED,
    VERIFIED_REFERENCE,
    wilson_interval,
)

# Ball-action-spotting style labels → HPFA video event families.
# BALL_RECOVERY from a successful tackle is a partial construct match: it
# covers tackle wins only, not interceptions or loose-ball recoveries.
BAS_LABEL_MAP = {
    "Shot": ("SHOT", "EXACT"),
    "Goal": ("GOAL", "EXACT"),
    "Free Kick": ("FREE_KICK", "EXACT"),
    "Throw In": ("THROW_IN", "EXACT"),
    "Player Successful Tackle": ("BALL_RECOVERY", "PARTIAL_TACKLE_WIN_ONLY"),
}
BAS_KNOWN_LABELS = {
    "Pass", "Drive", "Header", "High Pass", "Out", "Cross", "Throw In", "Shot",
    "Ball Player Block", "Player Successful Tackle", "Free Kick", "Goal",
}

DEFAULT_TOLERANCE_S = {
    "SHOT": 3.0,
    "GOAL": 15.0,
    "SET_PIECE_RESTART": 5.0,
    "FREE_KICK": 5.0,
    "CORNER_KICK": 5.0,
    "THROW_IN": 5.0,
    "KICK_OFF": 5.0,
    "BALL_RECOVERY": 3.0,
}


def load_bas_reference(path: str | Path, half: int) -> list[dict[str, Any]]:
    """Parse a BAS-format JSON (gameTime / position / label / team)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = []
    for i, ann in enumerate(data.get("annotations", [])):
        label = ann.get("label")
        if label not in BAS_KNOWN_LABELS:
            raise ValueError(f"unknown_reference_label:{label}")
        h = int(str(ann.get("gameTime", "0 - 0")).split(" - ")[0])
        if h != half:
            continue
        raw.append({"idx": i, "t": int(ann["position"]) / 1000.0, "label": label, "team": ann.get("team"), "player_id": ann.get("player_id"), "visibility": ann.get("visibility")})
    raw.sort(key=lambda r: (r["t"], r["idx"]))
    return derive_reference_events(raw)


RESTART_SUBTYPE_FROM_LABEL = {"Throw In": "THROW_IN", "Free Kick": "FREE_KICK"}


def derive_reference_events(raw: list[dict[str, Any]], out_restart_window_s: float = 60.0, goal_restart_window_s: float = 180.0) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for r in raw:
        if r["label"] in BAS_LABEL_MAP:
            family, match = BAS_LABEL_MAP[r["label"]]
            refs.append({"ref_id": f"ref_{r['idx']}", "event_type": family, "t": r["t"], "team": r["team"], "player_id": r["player_id"], "construct_match": match, "source_label": r["label"]})
    # Restarts: explicit restart labels + first labelled touch after Out/Goal.
    for i, r in enumerate(raw):
        if r["label"] in ("Free Kick", "Throw In"):
            refs.append({"ref_id": f"ref_{r['idx']}_restart", "event_type": "SET_PIECE_RESTART", "t": r["t"], "team": r["team"], "player_id": r["player_id"], "construct_match": "EXACT", "source_label": r["label"]})
        if r["label"] in ("Out", "Goal"):
            nxt = next((n for n in raw[i + 1:] if n["t"] > r["t"] and n["label"] not in ("Out", "Goal")), None)
            limit = goal_restart_window_s if r["label"] == "Goal" else out_restart_window_s
            if nxt is None or nxt["t"] - r["t"] > limit or nxt["label"] in ("Throw In", "Free Kick"):
                continue
            kind = "KICK_OFF" if r["label"] == "Goal" else "SET_PIECE_RESTART"
            subtype = "after_goal" if r["label"] == "Goal" else "after_out_goal_kick_or_corner"
            refs.append({"ref_id": f"ref_{nxt['idx']}_restart_{subtype}", "event_type": "SET_PIECE_RESTART", "t": nxt["t"], "team": nxt["team"], "player_id": nxt["player_id"], "construct_match": "DERIVED_" + subtype.upper(), "source_label": nxt["label"]})
            if kind == "KICK_OFF":
                refs.append({"ref_id": f"ref_{nxt['idx']}_kickoff", "event_type": "KICK_OFF", "t": nxt["t"], "team": nxt["team"], "player_id": nxt["player_id"], "construct_match": "DERIVED_AFTER_GOAL", "source_label": nxt["label"]})
    refs.sort(key=lambda x: (x["t"], x["event_type"]))
    return refs


def match_events(cands: list[dict[str, Any]], refs: list[dict[str, Any]], tolerance_s: float) -> tuple[list[tuple[dict, dict, float]], list[dict], list[dict]]:
    """Greedy one-to-one matching, highest score first (SoccerNet-style)."""
    used: set[str] = set()
    pairs = []
    unmatched_c = []
    for c in sorted(cands, key=lambda e: -e["score"]):
        best, best_d = None, None
        for r in refs:
            if r["ref_id"] in used:
                continue
            d = abs(c["video_time_s"] - r["t"])
            if d <= tolerance_s and (best_d is None or d < best_d):
                best, best_d = r, d
        if best is None:
            unmatched_c.append(c)
        else:
            used.add(best["ref_id"])
            pairs.append((c, best, float(best_d)))
    unmatched_r = [r for r in refs if r["ref_id"] not in used]
    return pairs, unmatched_c, unmatched_r


def _inside(t: float, windows: list[dict[str, Any]]) -> bool:
    return any(w["start_s"] <= t <= w["end_s"] for w in windows)


def evaluate(
    cands: list[dict[str, Any]],
    refs: list[dict[str, Any]],
    *,
    duration_s: float,
    triage_windows: list[dict[str, Any]],
    audit_windows: list[dict[str, Any]],
    tolerances: dict[str, float] | None = None,
    sweep: tuple[float, ...] = (1.0, 2.0, 5.0, 10.0),
) -> dict[str, Any]:
    tol = DEFAULT_TOLERANCE_S | (tolerances or {})
    hours = duration_s / 3600.0 if duration_s else None
    per: dict[str, Any] = {}
    for et in EVENT_TYPES:
        c = [e for e in cands if e["event_type"] == et]
        r = [e for e in refs if e["event_type"] == et]
        if not c and not r:
            continue
        pairs, fp, fn = match_events(c, r, tol[et])
        tp = len(pairs)
        prec_ci = wilson_interval(tp, len(c))
        rec_ci = wilson_interval(tp, len(r))
        in_triage = [x for x in r if _inside(x["t"], triage_windows)]
        in_audit = [x for x in r if _inside(x["t"], audit_windows)]
        in_audit_and_triage = [x for x in in_audit if _inside(x["t"], triage_windows)]
        per[et] = {
            "tolerance_s": tol[et],
            "candidates": len(c),
            "references": len(r),
            "true_positive": tp,
            "false_positive": len(fp),
            "false_negative": len(fn),
            "precision": round(tp / len(c), 4) if c else None,
            "precision_wilson95": [round(v, 4) for v in prec_ci] if prec_ci else None,
            "recall": round(tp / len(r), 4) if r else None,
            "recall_wilson95": [round(v, 4) for v in rec_ci] if rec_ci else None,
            "f1": round(2 * tp / (len(c) + len(r)), 4) if (c or r) else None,
            "false_positive_per_video_hour": round(len(fp) / hours, 3) if hours else None,
            "mean_abs_time_error_s": round(sum(d for *_, d in pairs) / tp, 3) if tp else None,
            "triage_window_recall_true": round(len(in_triage) / len(r), 4) if r else None,
            "triage_window_recall_random_audit_estimate": round(len(in_audit_and_triage) / len(in_audit), 4) if in_audit else None,
            "random_audit_reference_n": len(in_audit),
            "tolerance_sweep": {
                str(s): {
                    "tp": (k := len(match_events(c, r, s)[0])),
                    "precision": round(k / len(c), 4) if c else None,
                    "recall": round(k / len(r), 4) if r else None,
                }
                for s in sweep
            },
            "construct_match": sorted({x.get("construct_match", "EXACT") for x in r}),
        }
    return {"duration_s": duration_s, "per_event_type": per}


def admit_capability(
    per_event_type: dict[str, Any],
    *,
    min_references: int = 10,
    supported_lower_bound: float = 0.5,
    experimental_point: float = 0.3,
) -> dict[str, dict[str, Any]]:
    """Capability policy from held-out validation metrics.

    SUPPORTED_IN_VALIDATED_DOMAIN needs enough references and Wilson lower
    bounds of precision AND recall above `supported_lower_bound`.
    EXPERIMENTAL needs point precision and recall above `experimental_point`.
    Anything else, or no evidence, is NOT_SUPPORTED.
    """
    out = {}
    for et in EVENT_TYPES:
        m = per_event_type.get(et)
        if not m or not m.get("references"):
            out[et] = {"status": NOT_SUPPORTED, "reason": "no_reference_evidence"}
            continue
        p, r = m.get("precision") or 0.0, m.get("recall") or 0.0
        p_lo = (m.get("precision_wilson95") or [0, 0])[0]
        r_lo = (m.get("recall_wilson95") or [0, 0])[0]
        if m["references"] >= min_references and p_lo >= supported_lower_bound and r_lo >= supported_lower_bound:
            status, reason = SUPPORTED, "wilson_lower_bounds_above_threshold"
        elif p >= experimental_point and r >= experimental_point:
            status, reason = EXPERIMENTAL, "point_estimates_above_experimental_threshold"
        else:
            status, reason = NOT_SUPPORTED, "validation_metrics_below_threshold"
        out[et] = {"status": status, "reason": reason, "precision": p, "recall": r, "precision_lower95": p_lo, "recall_lower95": r_lo, "references": m["references"]}
    return out


def mark_reference_verified(cands: list[dict[str, Any]], refs: list[dict[str, Any]], tolerances: dict[str, float] | None = None, reference_source: str = "REFERENCE_LABELS") -> list[dict[str, Any]]:
    """Candidates matched to an independent reference become VERIFIED_REFERENCE.

    Team/player are copied only from the reference, with basis recorded.
    """
    tol = DEFAULT_TOLERANCE_S | (tolerances or {})
    out = [dict(c) for c in cands]
    by_id = {c["event_id"]: c for c in out}
    for et in EVENT_TYPES:
        c = [x for x in out if x["event_type"] == et]
        r = [x for x in refs if x["event_type"] == et]
        for cand, ref, d in match_events(c, r, tol[et])[0]:
            row = by_id[cand["event_id"]]
            row["verification_status"] = VERIFIED_REFERENCE
            row["verification_basis"] = {"source": reference_source, "ref_id": ref["ref_id"], "source_label": ref.get("source_label"), "time_delta_s": round(d, 3), "construct_match": ref.get("construct_match")}
            subtype = RESTART_SUBTYPE_FROM_LABEL.get(ref.get("source_label") or "")
            if et == "SET_PIECE_RESTART" and "after_goal" in str(ref.get("construct_match", "")).lower():
                subtype = "KICK_OFF"
            if et == "SET_PIECE_RESTART" and subtype:
                row["event_subtype"] = subtype
                row["event_subtype_basis"] = f"{reference_source}_LABEL"
            if ref.get("team") not in (None, ""):
                row["team"] = str(ref["team"])
                row["team_basis"] = f"{reference_source}_SIDE_LABEL_NOT_IDENTITY"
            if ref.get("player_id") not in (None, ""):
                row["player"] = str(ref["player_id"])
                row["player_basis"] = f"{reference_source}_PLAYER_ID"
    return out
