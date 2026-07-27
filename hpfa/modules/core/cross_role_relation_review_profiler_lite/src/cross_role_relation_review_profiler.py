from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "cross_role_relation_review_profiler_lite_v1"
INPUT_MODULE_ID = "cross_role_relation_candidate_resolver_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "CROSS_ROLE_RELATION_REVIEW_PROFILE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("resolver_input_unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError("resolver_input_invalid")
    return payload


def build_review_profile(payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("resolver_input_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append("resolver_hard_blocks_present")

    match_surface_binding_id = _clean(payload.get("match_surface_binding_id"))
    if not match_surface_binding_id:
        blocks.append("match_surface_binding_id_missing")

    records = payload.get("resolved_relation_candidates")
    if not isinstance(records, list):
        blocks.append("resolved_relation_candidates_invalid")
        records = []
    if payload.get("resolved_relation_candidate_count") != len(records):
        blocks.append("resolved_relation_candidate_count_mismatch")

    review_records: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    role_pair_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    taxonomy_context_counts: Counter[str] = Counter()
    family_reason_matrix: dict[str, Counter[str]] = defaultdict(Counter)

    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            blocks.append(f"relation_record_invalid:{index}")
            continue
        relation_id = _clean(record.get("resolved_relation_candidate_id"))
        if not relation_id:
            blocks.append(f"resolved_relation_candidate_id_missing:{index}")
        elif relation_id in seen_ids:
            blocks.append(f"duplicate_resolved_relation_candidate_id:{relation_id}")
        seen_ids.add(relation_id)

        record_binding_id = _clean(record.get("match_surface_binding_id"))
        if not record_binding_id:
            blocks.append(f"relation_match_surface_binding_id_missing:{relation_id or index}")
        elif match_surface_binding_id and record_binding_id != match_surface_binding_id:
            blocks.append(f"relation_match_surface_binding_id_mismatch:{relation_id or index}")

        if record.get("relation_candidate_is_event_truth") is True:
            blocks.append(f"event_truth_claimed:{relation_id or index}")
        if record.get("cross_role_fusion_allowed") is True:
            blocks.append(f"cross_role_fusion_claimed:{relation_id or index}")
        if record.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"relation_canonical_event_count_claimed:{relation_id or index}")

        if record.get("relation_record_status") != "REVIEW_REQUIRED":
            continue

        reasons = sorted({_clean(item) for item in (record.get("review_hits") or []) if _clean(item)})
        if not reasons:
            reasons = ["review_reason_missing"]
            reviews.append("review_reason_missing_present")

        family = _clean(record.get("action_family_candidate")) or "UNKNOWN_FAMILY"
        role_pair = "+".join(sorted(_clean(item) for item in (record.get("source_roles") or []) if _clean(item))) or "UNKNOWN_ROLE_PAIR"
        classification = _clean(record.get("relation_classification")) or "UNKNOWN_CLASSIFICATION"
        taxonomy_ids = sorted({_clean(item) for item in (record.get("taxonomy_context_record_ids") or []) if _clean(item)})
        taxonomy_state = "TAXONOMY_CONTEXT_PRESENT" if taxonomy_ids else "TAXONOMY_CONTEXT_ABSENT"

        for reason in reasons:
            reason_counts[reason] += 1
            family_reason_matrix[family][reason] += 1
        family_counts[family] += 1
        role_pair_counts[role_pair] += 1
        classification_counts[classification] += 1
        taxonomy_context_counts[taxonomy_state] += 1

        review_records.append(
            {
                "resolved_relation_candidate_id": relation_id,
                "source_relation_candidate_id": record.get("source_relation_candidate_id"),
                "match_surface_binding_id": record_binding_id,
                "action_family_candidate": family,
                "source_role_pair": role_pair,
                "relation_classification": classification,
                "taxonomy_context_record_ids": taxonomy_ids,
                "review_reasons": reasons,
                "actor_identity_candidate_id": record.get("actor_identity_candidate_id"),
                "team_identity_candidate_id": record.get("team_identity_candidate_id"),
                "period_candidate": record.get("period_candidate"),
                "start_candidate": record.get("start_candidate"),
                "end_candidate": record.get("end_candidate"),
                "pos_x_candidate": record.get("pos_x_candidate"),
                "pos_y_candidate": record.get("pos_y_candidate"),
                "profile_only": True,
                "event_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )

    expected_review_count = payload.get("review_required_relation_count")
    if expected_review_count != len(review_records):
        blocks.append("review_required_relation_count_mismatch")
    if review_records:
        reviews.append("cross_role_relation_reviews_profiled")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if review_records else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": match_surface_binding_id,
        "source_resolved_relation_candidate_count": len(records),
        "profiled_review_relation_count": len(review_records),
        "review_reason_counts": dict(sorted(reason_counts.items())),
        "review_family_counts": dict(sorted(family_counts.items())),
        "review_role_pair_counts": dict(sorted(role_pair_counts.items())),
        "review_classification_counts": dict(sorted(classification_counts.items())),
        "taxonomy_context_counts": dict(sorted(taxonomy_context_counts.items())),
        "family_reason_matrix": {key: dict(sorted(value.items())) for key, value in sorted(family_reason_matrix.items())},
        "review_relation_profiles": review_records,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "profile_resolves_relations": False,
        "count_value_output_allowed": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "claim_ceiling": CLAIM_CEILING,
        "production_release": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    out = validate_out(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = build_review_profile(load_json(args.input))
    (out / "cross_role_relation_review_profiler_lite_v1.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "cross_role_relation_review_profiler_lite_v1.txt").write_text(
        "\n".join(
            [
                f"status={result['status']}",
                f"profiled_review_relation_count={result['profiled_review_relation_count']}",
                f"review_reason_counts={json.dumps(result['review_reason_counts'], ensure_ascii=False, sort_keys=True)}",
                f"canonical_event_count={CANONICAL_EVENT_COUNT}",
                "production_release=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 1 if result["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
