"""Projection of video event rows into HPFA surfaces + human review loop.

- `hpfa_surface/video_event_surface_verified_v1.csv` holds VERIFIED_* rows only
  and uses column names that `csv_surface_reader_lite` resolves (team,
  event_type, subtype, period, start_time_s, end_time_s).
- Candidates go to a JSON file and a review queue TSV, never to the surface.
- Counterfactual rows are rejected here by construction.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from hvi_contract import (
    CANONICAL_EVENT_COUNT,
    CLAIM_BOUNDARY,
    CLAIM_CEILING,
    DOES_NOT_MEASURE,
    HPFA_CSV_EVENT_TYPE,
    MODULE_ID,
    OBSERVED_LAYER,
    REJECTED,
    UNKNOWN,
    VERIFIED_HUMAN,
    VERIFIED_STATES,
    validate_event,
)

SURFACE_DIR = "hpfa_surface"
SURFACE_CSV = "video_event_surface_verified_v1.csv"
SURFACE_COLUMNS = (
    "event_id",
    "period",
    "start_time_s",
    "end_time_s",
    "video_timestamp",
    "team",
    "event_type",
    "subtype",
    "player",
    "verification_status",
    "verification_source",
    "detector_id",
    "score",
    "time_uncertainty_s",
    "capability_status",
    "source_video_id",
    "source_fingerprint",
    "evidence_kind",
)
REVIEW_COLUMNS = (
    "event_id",
    "video_timestamp",
    "video_time_s",
    "event_type",
    "event_subtype",
    "score",
    "capability_status",
    "clip_start_s",
    "clip_end_s",
    "decision",
    "corrected_event_type",
    "team",
    "player",
    "reviewer",
    "note",
)
REVIEW_DECISIONS = {"CONFIRM", "REJECT", "RELABEL", ""}


def envelope(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": status,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "claim_ceiling": CLAIM_CEILING,
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "does_not_measure": list(DOES_NOT_MEASURE),
        "active_match_evidence_pass": False,
        "production_release": False,
    } | extra


def surface_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for ev in events:
        if ev.get("layer") != OBSERVED_LAYER:
            raise ValueError("non_observed_layer_row_in_surface_export")
        if ev.get("verification_status") not in VERIFIED_STATES:
            continue
        problems = validate_event(ev)
        if problems:
            raise ValueError("event_contract_violation:" + ",".join(problems))
        etype, subtype = HPFA_CSV_EVENT_TYPE[ev["event_type"]]
        if ev["event_type"] == "SET_PIECE_RESTART" and ev.get("event_subtype") in HPFA_CSV_EVENT_TYPE and ev.get("event_subtype_basis"):
            # Restart type is taken only from a reference/human basis, never guessed.
            etype, subtype = HPFA_CSV_EVENT_TYPE[ev["event_subtype"]]
        basis = ev.get("verification_basis") or {}
        rows.append(
            {
                "event_id": ev["event_id"],
                "period": ev.get("period", UNKNOWN),
                "start_time_s": f"{ev['video_time_s']:.3f}",
                "end_time_s": f"{(ev.get('video_time_end_s') or ev['video_time_s']):.3f}",
                "video_timestamp": ev["video_timestamp"],
                "team": ev.get("team", UNKNOWN),
                "event_type": etype,
                "subtype": subtype,
                "player": ev.get("player", UNKNOWN),
                "verification_status": ev["verification_status"],
                "verification_source": basis.get("source", ""),
                "detector_id": ev["detector_id"],
                "score": f"{ev['score']:.4f}",
                "time_uncertainty_s": f"{ev['time_uncertainty_s']:.3f}",
                "capability_status": ev["capability_status"],
                "source_video_id": ev["source_video_id"],
                "source_fingerprint": ev["source_fingerprint"],
                "evidence_kind": ev["evidence_kind"],
            }
        )
    return rows


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, Any]], delimiter: str = ",") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_review_queue(path: Path, events: list[dict[str, Any]], pad_s: float = 8.0) -> int:
    rows = []
    for ev in events:
        if ev.get("verification_status") in VERIFIED_STATES or ev.get("verification_status") == REJECTED:
            continue
        rows.append(
            {
                "event_id": ev["event_id"],
                "video_timestamp": ev["video_timestamp"],
                "video_time_s": ev["video_time_s"],
                "event_type": ev["event_type"],
                "event_subtype": ev.get("event_subtype", UNKNOWN),
                "score": ev["score"],
                "capability_status": ev["capability_status"],
                "clip_start_s": round(max(0.0, ev["video_time_s"] - pad_s), 3),
                "clip_end_s": round(ev["video_time_s"] + pad_s, 3),
                "decision": "",
                "corrected_event_type": "",
                "team": "",
                "player": "",
                "reviewer": "",
                "note": "",
            }
        )
    write_csv(path, REVIEW_COLUMNS, rows, delimiter="\t")
    return len(rows)


def apply_review(events: list[dict[str, Any]], review_tsv: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Merge human decisions. CONFIRM/RELABEL require a reviewer name."""
    with Path(review_tsv).open(encoding="utf-8", newline="") as handle:
        decisions = {r["event_id"]: r for r in csv.DictReader(handle, delimiter="\t")}
    out, stats = [], {"confirmed": 0, "rejected": 0, "relabelled": 0, "pending": 0, "invalid": []}
    for ev in events:
        ev = dict(ev)
        d = decisions.get(ev["event_id"])
        decision = (d or {}).get("decision", "").strip().upper()
        if d is None or decision == "":
            stats["pending"] += int(ev["verification_status"] not in VERIFIED_STATES)
            out.append(ev)
            continue
        if decision not in REVIEW_DECISIONS or not d.get("reviewer", "").strip():
            stats["invalid"].append(ev["event_id"])
            out.append(ev)
            continue
        basis = {"source": "HUMAN_REVIEW", "reviewer": d["reviewer"].strip(), "note": d.get("note", "")}
        if decision == "REJECT":
            ev["verification_status"] = REJECTED
            ev["verification_basis"] = basis
            stats["rejected"] += 1
        else:
            if decision == "RELABEL":
                new_type = d.get("corrected_event_type", "").strip().upper()
                if new_type not in HPFA_CSV_EVENT_TYPE:
                    stats["invalid"].append(ev["event_id"])
                    out.append(ev)
                    continue
                basis["relabelled_from"] = ev["event_type"]
                ev["event_type"] = new_type
                stats["relabelled"] += 1
            else:
                stats["confirmed"] += 1
            ev["verification_status"] = VERIFIED_HUMAN
            ev["verification_basis"] = basis
            ev["evidence_kind"] = "HUMAN_REVIEW"
            if d.get("team", "").strip():
                ev["team"] = d["team"].strip()
                ev["team_basis"] = "HUMAN_REVIEW_VISUAL"
            if d.get("player", "").strip():
                ev["player"] = d["player"].strip()
                ev["player_basis"] = "HUMAN_REVIEW_VISUAL"
        out.append(ev)
    return out, stats


def write_event_outputs(out_dir: str | Path, events: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, str]:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    violations = {ev["event_id"]: validate_event(ev) for ev in events}
    violations = {k: v for k, v in violations.items() if v}
    verified = [e for e in events if e["verification_status"] in VERIFIED_STATES]
    status = "FAIL_CLOSED" if violations else ("PASS" if verified else "REVIEW_REQUIRED")
    payload = envelope(
        status,
        event_rows=events,
        event_row_count=len(events),
        verified_row_count=len(verified),
        contract_violations=violations,
        hard_block_hits=["event_contract_violation"] if violations else [],
        safe_statement=(
            "Rows are video-derived candidates; only VERIFIED_* rows carry an independent "
            "reference or human-review basis. Team/player are UNKNOWN unless that basis exists."
        ),
    ) | meta
    paths = {
        "events_json": root / "video_events_v1.json",
        "review_queue": root / "video_event_review_queue_v1.tsv",
        "surface_csv": root / SURFACE_DIR / SURFACE_CSV,
    }
    paths["events_json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    write_review_queue(paths["review_queue"], events)
    if not violations:
        write_csv(paths["surface_csv"], SURFACE_COLUMNS, surface_rows(events))
    return {k: str(v) for k, v in paths.items()}
