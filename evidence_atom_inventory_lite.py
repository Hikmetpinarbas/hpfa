from __future__ import annotations

import argparse
import json
from pathlib import Path

import row_nucleus_inventory as current_row_nucleus
from hpfa.modules.core.evidence_atom_inventory_lite.src import evidence_atom_inventory as atoms
from hpfa.modules.core.provider_label_value_semantics_lite.src import (
    provider_label_value_semantics as semantics,
)

ROOT = Path(__file__).resolve().parent
REGISTRY = (
    ROOT
    / "hpfa"
    / "modules"
    / "core"
    / "provider_label_value_semantics_lite"
    / "registry"
    / "sportsbase_label_semantics_seed_v1.json"
)


def _decorate_current_context(payload: dict, row_payload: dict) -> dict:
    payload["current_row_nucleus_status"] = row_payload.get("status")
    payload["current_content_source_role_bridge_status"] = row_payload.get(
        "content_source_role_bridge_status"
    )
    payload["current_row_nucleus_candidate_count"] = row_payload.get(
        "row_nucleus_candidate_count"
    )
    payload["current_row_nucleus_pass_count"] = row_payload.get("row_nucleus_pass_count")
    payload["current_row_nucleus_review_required_count"] = row_payload.get(
        "row_nucleus_review_required_count"
    )
    return payload


def _failure_from_row_payload(row_payload: dict) -> dict:
    return {
        "module_id": atoms.MODULE_ID,
        "status": "FAIL_CLOSED",
        "module_status": "FAIL_CLOSED",
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": None,
        "source_row_nucleus_candidate_count": row_payload.get("row_nucleus_candidate_count", 0),
        "evidence_atom_count": 0,
        "evidence_atom_pass_count": 0,
        "evidence_atom_review_required_count": 0,
        "atom_class_counts": {},
        "semantic_role_counts": {},
        "evidence_atoms": [],
        "hard_block_hits": ["current_row_nucleus_fail_closed"],
        "review_hits": [],
        "event_instance_count": 0,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "physical_action_identity_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": atoms.CLAIM_CEILING,
        "current_row_nucleus_status": row_payload.get("status"),
    }


def build_from_existing_row_payload(row_payload: dict, input_dir: str | Path) -> dict:
    """Build Evidence Atom candidates from the already-produced Row Nucleus payload.

    This preserves shared-foundation single execution in orchestrated paths. It
    does not create or strengthen Row Nucleus truth; the supplied payload remains
    the current producer output and all existing claim ceilings stay closed.
    """
    if row_payload.get("status") == "FAIL_CLOSED":
        return _failure_from_row_payload(row_payload)
    registry = semantics.load_registry(REGISTRY)
    payload = atoms.build_evidence_atom_inventory(row_payload, input_dir, registry)
    return _decorate_current_context(payload, row_payload)


def runtime_build_report(input_dir: str | Path) -> dict:
    row_payload = current_row_nucleus.runtime_build_report(input_dir, root=ROOT)
    return build_from_existing_row_payload(row_payload, input_dir)


def write_outputs_from_existing_row_payload(
    row_payload: dict,
    input_dir: str | Path,
    out_dir: str | Path,
) -> dict:
    output = atoms.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload = build_from_existing_row_payload(row_payload, input_dir)
    paths = atoms.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = atoms.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    row_payload = current_row_nucleus.runtime_write_outputs(input_dir, output, root=ROOT)
    return write_outputs_from_existing_row_payload(row_payload, input_dir, output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current Row Nucleus to Evidence Atom migration adapter"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "current_row_nucleus_status": payload.get("current_row_nucleus_status"),
                "content_source_role_bridge_status": payload.get(
                    "current_content_source_role_bridge_status"
                ),
                "evidence_atom_count": payload.get("evidence_atom_count"),
                "evidence_atom_pass_count": payload.get("evidence_atom_pass_count"),
                "evidence_atom_review_required_count": payload.get(
                    "evidence_atom_review_required_count"
                ),
                "atom_class_counts": payload.get("atom_class_counts") or {},
                "hard_block_hits": payload.get("hard_block_hits") or [],
                "review_hits": payload.get("review_hits") or [],
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
                "outputs": payload.get("outputs") or {},
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
