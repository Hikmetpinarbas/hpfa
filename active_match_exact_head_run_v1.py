from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import active_match_spine_runner as canonical_runner
import analyst_output_claim_admission_current_v1 as claim_admission_runner
import safe_finding_admission_current_v1 as safe_finding_runner

MODULE_ID = "active_match_exact_head_run_v1"
ACTIVE_MATCH_RELATIVE_PATH = Path("runtime/active_single_match/current")
FULL_SPINE_JSON = "active_match_full_spine_v1.json"
SEQUENCE_JSON = "visible_action_sequence_candidates_lite_v1.json"
SAFE_FINDING_ADMISSION_JSON = "safe_finding_admission_projection_v1.json"
ANALYST_OUTPUT_CLAIM_JSON = "analyst_output_claim_contract_projection_v1.json"
OUTPUT_JSON = "active_match_exact_head_run_v1.json"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"


def _git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _runtime_authority_root(match_dir: Path) -> Path:
    suffix = ACTIVE_MATCH_RELATIVE_PATH.parts
    if tuple(match_dir.parts[-len(suffix):]) != tuple(suffix):
        raise ValueError(f"runtime_authority_path_invalid:{match_dir}")
    root = match_dir
    for _ in suffix:
        root = root.parent
    return root


def _run_canonical_full_spine(
    *,
    match_dir: Path,
    out_dir: Path,
    repo_root: Path,
    runtime_authority_root: Path,
    expected_product_commit: str,
) -> dict[str, Any]:
    product_commit = _git_head(repo_root)
    expected = str(expected_product_commit or "").strip()
    command = [
        sys.executable,
        "active_match_spine_runner.py",
        str(match_dir),
        "--out-dir",
        str(out_dir),
        "--full-spine",
        "--execution-root",
        str(repo_root),
    ]

    if not expected or product_commit != expected:
        return {
            "command": command,
            "returncode": 2,
            "passed": False,
            "stdout": "",
            "stderr": "product_commit_mismatch_or_unavailable",
            "product_execution_root": str(repo_root),
            "runtime_authority_root": str(runtime_authority_root),
            "product_commit": product_commit,
            "expected_product_commit": expected or None,
            "product_commit_matches_expected": False,
            "exact_head_authority_separation_enforced": True,
        }

    original_validate = canonical_runner.full_spine_module.validate_active_match_authority
    original_argv = list(sys.argv)
    stdout = io.StringIO()
    stderr = io.StringIO()

    def validate_runtime_authority(path: str | Path, _product_execution_root: str | Path) -> Path:
        return original_validate(path, runtime_authority_root)

    returncode = 2
    try:
        canonical_runner.full_spine_module.validate_active_match_authority = validate_runtime_authority
        sys.argv = command[1:]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                value = canonical_runner.main()
                returncode = int(value or 0)
            except SystemExit as exc:
                returncode = int(exc.code or 0) if isinstance(exc.code, int) else 2
    except Exception as exc:
        stderr.write(f"canonical_full_spine_exception:{type(exc).__name__}")
        returncode = 2
    finally:
        canonical_runner.full_spine_module.validate_active_match_authority = original_validate
        sys.argv = original_argv

    return {
        "command": command,
        "returncode": returncode,
        "passed": returncode == 0,
        "stdout": stdout.getvalue().strip(),
        "stderr": stderr.getvalue().strip(),
        "product_execution_root": str(repo_root),
        "runtime_authority_root": str(runtime_authority_root),
        "product_commit": product_commit,
        "expected_product_commit": expected,
        "product_commit_matches_expected": True,
        "exact_head_authority_separation_enforced": True,
    }


def _run_post_sequence_admission(out_dir: Path) -> dict[str, Any]:
    """Run only the two compact post-sequence decision gears.

    These gears consume the already-produced sequence artifact. They do not rebuild
    sequence/counterevidence or create new evidence.
    """
    sequence_path = out_dir / SEQUENCE_JSON
    if not sequence_path.is_file():
        return {
            "status": "FAIL_CLOSED",
            "reason": "sequence_artifact_missing",
            "safe_finding_admission": {},
            "analyst_output_claim": {},
        }

    try:
        admission = safe_finding_runner.runtime_write_outputs(sequence_path, out_dir)
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "reason": f"safe_finding_admission_exception:{type(exc).__name__}",
            "safe_finding_admission": {},
            "analyst_output_claim": {},
        }

    if admission.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "reason": "safe_finding_admission_fail_closed",
            "safe_finding_admission": admission,
            "analyst_output_claim": {},
        }

    admission_path = out_dir / SAFE_FINDING_ADMISSION_JSON
    try:
        claim = claim_admission_runner.runtime_write_outputs(
            sequence_path,
            admission_path,
            out_dir,
        )
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "reason": f"analyst_output_claim_admission_exception:{type(exc).__name__}",
            "safe_finding_admission": admission,
            "analyst_output_claim": {},
        }

    if claim.get("status") == "FAIL_CLOSED":
        return {
            "status": "FAIL_CLOSED",
            "reason": "analyst_output_claim_admission_fail_closed",
            "safe_finding_admission": admission,
            "analyst_output_claim": claim,
        }

    return {
        "status": "PASS",
        "reason": None,
        "safe_finding_admission": admission,
        "analyst_output_claim": claim,
    }


def _post_sequence_admission_ready(
    *,
    out_dir: Path,
    sequence: dict[str, Any],
    post_sequence: dict[str, Any],
) -> bool:
    admission = post_sequence.get("safe_finding_admission") or {}
    claim = post_sequence.get("analyst_output_claim") or {}
    expected_count = int(sequence.get("safe_finding_handoff_candidate_count") or 0)
    admission_count = int(admission.get("safe_finding_admission_decision_count") or 0)
    claim_count = int(claim.get("analyst_output_contract_count") or 0)
    return (
        post_sequence.get("status") == "PASS"
        and (out_dir / SAFE_FINDING_ADMISSION_JSON).is_file()
        and (out_dir / ANALYST_OUTPUT_CLAIM_JSON).is_file()
        and admission.get("status") != "FAIL_CLOSED"
        and claim.get("status") != "FAIL_CLOSED"
        and claim.get("safe_finding_admission_consumed") is True
        and admission_count == expected_count
        and claim_count == expected_count
        and admission.get("canonical_event_count") == "UNKNOWN"
        and admission.get("true_action_count") == "UNKNOWN"
        and admission.get("production_release") is False
        and claim.get("canonical_event_count") == "UNKNOWN"
        and claim.get("true_action_count") == "UNKNOWN"
        and claim.get("production_release") is False
    )


def _admission_gated_full_spine_for_user_outputs(
    *,
    out_dir: Path,
    full_spine: dict[str, Any],
    sequence: dict[str, Any],
    post_sequence: dict[str, Any],
) -> dict[str, Any]:
    """Replace legacy C4 report sentences with explicitly admitted Safe Findings only.

    This is an output projection. It creates no evidence, does not rebuild sequence
    intelligence, and never strengthens the upstream claim ceiling.
    """
    admission = post_sequence.get("safe_finding_admission") or {}
    claim = post_sequence.get("analyst_output_claim") or {}
    if post_sequence.get("status") != "PASS":
        return {"status": "FAIL_CLOSED", "reason": "post_sequence_admission_not_pass"}

    handoff_by_ref: dict[str, dict[str, Any]] = {}
    for row in sequence.get("safe_finding_handoff_candidates") or []:
        if not isinstance(row, dict):
            return {"status": "FAIL_CLOSED", "reason": "safe_finding_handoff_not_object"}
        ref = str(row.get("safe_finding_handoff_candidate_id") or "").strip()
        if not ref:
            return {"status": "FAIL_CLOSED", "reason": "safe_finding_handoff_ref_missing"}
        if ref in handoff_by_ref:
            return {"status": "FAIL_CLOSED", "reason": f"duplicate_safe_finding_handoff_ref:{ref}"}
        handoff_by_ref[ref] = row

    admission_emit_refs: set[str] = set()
    for row in admission.get("safe_finding_admission_decisions") or []:
        if not isinstance(row, dict):
            return {"status": "FAIL_CLOSED", "reason": "safe_finding_admission_row_not_object"}
        if str(row.get("decision") or "").strip().upper() != "EMIT":
            continue
        if row.get("claim_output_allowed") is not True:
            return {"status": "FAIL_CLOSED", "reason": "emit_without_claim_output_allowed"}
        ref = str(row.get("source_safe_finding_handoff_ref") or "").strip()
        if not ref:
            return {"status": "FAIL_CLOSED", "reason": "emit_admission_source_ref_missing"}
        if ref in admission_emit_refs:
            return {"status": "FAIL_CLOSED", "reason": f"duplicate_emit_admission_ref:{ref}"}
        admission_emit_refs.add(ref)

    allowed: list[tuple[str, str]] = []
    allowed_refs: set[str] = set()
    for row in claim.get("analyst_output_contracts") or []:
        if not isinstance(row, dict):
            return {"status": "FAIL_CLOSED", "reason": "analyst_output_contract_not_object"}
        if row.get("professional_emit_allowed") is not True:
            continue
        if str(row.get("safe_finding_admission_decision") or "").strip().upper() != "EMIT":
            return {"status": "FAIL_CLOSED", "reason": "professional_emit_without_emit_decision"}
        ref = str(row.get("source_safe_finding_handoff_ref") or "").strip()
        if not ref:
            return {"status": "FAIL_CLOSED", "reason": "professional_emit_source_ref_missing"}
        if ref in allowed_refs:
            return {"status": "FAIL_CLOSED", "reason": f"duplicate_professional_emit_ref:{ref}"}
        handoff = handoff_by_ref.get(ref)
        if handoff is None:
            return {"status": "FAIL_CLOSED", "reason": f"professional_emit_handoff_missing:{ref}"}
        safe_meaning = str(handoff.get("safe_meaning") or "").strip()
        if not safe_meaning:
            return {"status": "FAIL_CLOSED", "reason": f"professional_emit_safe_meaning_missing:{ref}"}
        allowed_refs.add(ref)
        allowed.append((ref, safe_meaning))

    expected_emit_count = int(claim.get("professional_emit_allowed_count") or 0)
    admitted_emit_count = int(admission.get("professional_finding_emitted_count") or 0)
    if len(allowed) != expected_emit_count or len(allowed) != admitted_emit_count:
        return {"status": "FAIL_CLOSED", "reason": "professional_emit_count_mismatch"}
    if allowed_refs != admission_emit_refs:
        return {"status": "FAIL_CLOSED", "reason": "professional_emit_ref_mismatch"}

    engineering = full_spine.get("engineering_evidence")
    engineering = dict(engineering) if isinstance(engineering, dict) else {}
    if allowed and engineering.get("current_c4_producers_reused") is not True:
        return {"status": "FAIL_CLOSED", "reason": "professional_emit_without_current_c4_surface"}

    gated = dict(full_spine)
    gated["engineering_evidence"] = engineering
    gated["intelligence_chains"] = [
        {
            "source_safe_finding_handoff_ref": ref,
            "professional_finding_admission": "EMIT",
            "safe_sentence": {
                "safe_sentence_candidate_tr": safe_meaning,
            },
        }
        for ref, safe_meaning in allowed
    ]
    gated["intelligence_chain_count"] = len(allowed)
    gated["professional_finding_emitted_count"] = len(allowed)
    gated["analyst_output_admission_gated"] = True
    gated["canonical_event_count"] = "UNKNOWN"
    gated["true_action_count"] = "UNKNOWN"
    gated["production_release"] = False

    engineering["safe_finding_admission_consumed_for_user_output"] = True
    engineering["analyst_output_claim_contract_consumed_for_user_output"] = True
    engineering["legacy_c4_safe_sentences_used_for_professional_output"] = False
    engineering["admitted_professional_finding_output_count"] = len(allowed)

    current_artifacts = [
        str(value)
        for value in (full_spine.get("current_invocation_artifacts") or [])
        if str(value or "").strip()
    ]
    current_artifacts.extend(
        [
            str(out_dir / SAFE_FINDING_ADMISSION_JSON),
            str(out_dir / ANALYST_OUTPUT_CLAIM_JSON),
        ]
    )
    gated["current_invocation_artifacts"] = sorted(set(current_artifacts))
    return {
        "status": "PASS",
        "reason": None,
        "full_spine": gated,
        "admitted_professional_finding_output_count": len(allowed),
        "admitted_professional_finding_refs": sorted(allowed_refs),
    }


def _rewrite_standard_user_outputs_after_admission(
    *,
    out_dir: Path,
    full_spine: dict[str, Any],
    sequence: dict[str, Any],
    post_sequence: dict[str, Any],
) -> dict[str, Any]:
    gated = _admission_gated_full_spine_for_user_outputs(
        out_dir=out_dir,
        full_spine=full_spine,
        sequence=sequence,
        post_sequence=post_sequence,
    )
    if gated.get("status") != "PASS":
        return {
            "status": "FAIL_CLOSED",
            "reason": gated.get("reason") or "user_output_admission_gate_failed",
            "outputs": {},
            "admitted_professional_finding_output_count": 0,
        }

    try:
        outputs = canonical_runner.write_standard_user_outputs(
            out_dir,
            gated["full_spine"],
        )
    except Exception as exc:
        return {
            "status": "FAIL_CLOSED",
            "reason": f"admission_gated_user_output_exception:{type(exc).__name__}",
            "outputs": {},
            "admitted_professional_finding_output_count": 0,
        }

    required = {
        "analyst_report": outputs.get("analyst_report"),
        "bundle_manifest": outputs.get("bundle_manifest"),
        "bundle_zip": outputs.get("bundle_zip"),
    }
    missing = [
        key
        for key, value in required.items()
        if not value or not Path(str(value)).is_file()
    ]
    if missing:
        return {
            "status": "FAIL_CLOSED",
            "reason": f"admission_gated_user_output_missing:{','.join(sorted(missing))}",
            "outputs": outputs,
            "admitted_professional_finding_output_count": 0,
        }

    return {
        "status": "PASS",
        "reason": None,
        "outputs": outputs,
        "admitted_professional_finding_output_count": int(
            gated.get("admitted_professional_finding_output_count") or 0
        ),
        "admitted_professional_finding_refs": list(
            gated.get("admitted_professional_finding_refs") or []
        ),
        "analyst_report_admission_gated": True,
        "bundle_includes_safe_finding_admission": (out_dir / SAFE_FINDING_ADMISSION_JSON).is_file(),
        "bundle_includes_analyst_output_claim": (out_dir / ANALYST_OUTPUT_CLAIM_JSON).is_file(),
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run the canonical HPFA ACTIVE_MATCH full spine from an exact product checkout while preserving the separate runtime authority root."
    )
    parser.add_argument("--match-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--expected-product-commit", required=True)
    args = parser.parse_args()

    match_dir = Path(args.match_dir).expanduser().resolve(strict=False)
    out_dir = Path(args.out_dir).expanduser().resolve(strict=False)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        runtime_authority_root = _runtime_authority_root(match_dir)
    except ValueError as exc:
        payload = {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "ACTIVE_MATCH_RUNTIME_AUTHORITY_REJECTED",
            "hard_block_hits": [str(exc)],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
        }
        (out_dir / OUTPUT_JSON).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 2

    canonical = _run_canonical_full_spine(
        match_dir=match_dir,
        out_dir=out_dir,
        repo_root=repo_root,
        runtime_authority_root=runtime_authority_root,
        expected_product_commit=args.expected_product_commit,
    )

    full_spine = _load(out_dir / FULL_SPINE_JSON)
    sequence = _load(out_dir / SEQUENCE_JSON)
    post_sequence = (
        _run_post_sequence_admission(out_dir)
        if canonical.get("passed") is True and bool(sequence)
        else {
            "status": "FAIL_CLOSED",
            "reason": "canonical_or_sequence_not_ready",
            "safe_finding_admission": {},
            "analyst_output_claim": {},
        }
    )
    admission = post_sequence.get("safe_finding_admission") or {}
    claim = post_sequence.get("analyst_output_claim") or {}

    authority_separation_valid = (
        canonical.get("exact_head_authority_separation_enforced") is True
        and canonical.get("product_execution_root") == str(repo_root)
        and canonical.get("runtime_authority_root") == str(runtime_authority_root)
        and repo_root != runtime_authority_root
    )
    exact_product_commit_verified = canonical.get("product_commit_matches_expected") is True
    post_sequence_admission_ready = _post_sequence_admission_ready(
        out_dir=out_dir,
        sequence=sequence,
        post_sequence=post_sequence,
    ) if sequence else False
    user_output_gate = (
        _rewrite_standard_user_outputs_after_admission(
            out_dir=out_dir,
            full_spine=full_spine,
            sequence=sequence,
            post_sequence=post_sequence,
        )
        if post_sequence_admission_ready and bool(full_spine)
        else {
            "status": "FAIL_CLOSED",
            "reason": "post_sequence_admission_or_full_spine_not_ready",
            "outputs": {},
            "admitted_professional_finding_output_count": 0,
        }
    )
    user_output_admission_ready = user_output_gate.get("status") == "PASS"
    acceptance_surface_ready = (
        canonical.get("passed") is True
        and authority_separation_valid
        and exact_product_commit_verified
        and bool(full_spine)
        and bool(sequence)
        and post_sequence_admission_ready
        and user_output_admission_ready
    )

    payload = {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if acceptance_surface_ready else "FAIL_CLOSED",
        "decision": (
            "EXACT_HEAD_ACTIVE_MATCH_EVIDENCE_SURFACE_EVALUATED"
            if acceptance_surface_ready
            else "EXACT_HEAD_ACTIVE_MATCH_EVIDENCE_SURFACE_INCOMPLETE"
        ),
        "canonical_orchestrator": "active_match_spine_runner.py --full-spine",
        "parallel_runtime_engine_created": False,
        "product_code_root": str(repo_root),
        "runtime_authority_root": str(runtime_authority_root),
        "product_code_root_equals_runtime_authority_root": repo_root == runtime_authority_root,
        "product_runtime_authority_separation_valid": authority_separation_valid,
        "product_code_commit": canonical.get("product_commit"),
        "expected_product_commit": canonical.get("expected_product_commit"),
        "exact_product_commit_verified": exact_product_commit_verified,
        "canonical_full_spine_run": canonical,
        "canonical_full_spine_status": full_spine.get("status"),
        "canonical_full_spine_decision": full_spine.get("decision"),
        "sequence_status": sequence.get("status"),
        "primary_sequence_projection_mode": sequence.get("primary_sequence_projection_mode"),
        "occurrence_temporal_sequence_candidate_count": int(sequence.get("occurrence_temporal_sequence_candidate_count") or 0),
        "partial_order_occurrence_variant_count": int(sequence.get("partial_order_occurrence_variant_count") or 0),
        "dependency_aware_partial_order_similarity_pair_count": int(sequence.get("dependency_aware_partial_order_similarity_pair_count") or 0),
        "recurrence_candidate_eligible_pair_count": int(sequence.get("recurrence_candidate_eligible_pair_count") or 0),
        "anchor_centered_sequence_branch_map_count": int(sequence.get("anchor_centered_sequence_branch_map_count") or 0),
        "first_supported_branch_divergence_candidate_count": int(sequence.get("first_supported_branch_divergence_candidate_count") or 0),
        "comparison_eligible_outcome_record_count": int(sequence.get("comparison_eligible_outcome_record_count") or 0),
        "comparable_outcome_counterevidence_record_count": int(sequence.get("comparable_outcome_counterevidence_record_count") or 0),
        "comparable_outcome_contrast_state_counts": dict(sequence.get("comparable_outcome_contrast_state_counts") or {}),
        "comparable_counterevidence_candidate_count": int(sequence.get("comparable_counterevidence_candidate_count") or 0),
        "counterevidence_independent_support_count": int(sequence.get("counterevidence_independent_support_count") or 0),
        "safe_finding_handoff_candidate_count": int(sequence.get("safe_finding_handoff_candidate_count") or 0),
        "safe_finding_admission_status": admission.get("status"),
        "safe_finding_admission_decision_count": int(admission.get("safe_finding_admission_decision_count") or 0),
        "safe_finding_admission_decision_counts": dict(admission.get("finding_status_counts") or {}),
        "analyst_output_claim_status": claim.get("status"),
        "analyst_output_claim_contract_count": int(claim.get("analyst_output_contract_count") or 0),
        "safe_finding_admission_consumed_by_claim_contract": claim.get("safe_finding_admission_consumed") is True,
        "post_sequence_admission_ready": post_sequence_admission_ready,
        "analyst_user_output_admission_gate_status": user_output_gate.get("status"),
        "analyst_user_output_admission_gate_reason": user_output_gate.get("reason"),
        "analyst_report_admission_gated": user_output_gate.get("analyst_report_admission_gated") is True,
        "admitted_professional_finding_output_count": int(
            user_output_gate.get("admitted_professional_finding_output_count") or 0
        ),
        "admitted_professional_finding_output_refs": list(
            user_output_gate.get("admitted_professional_finding_refs") or []
        ),
        "bundle_includes_safe_finding_admission": user_output_gate.get(
            "bundle_includes_safe_finding_admission"
        ) is True,
        "bundle_includes_analyst_output_claim": user_output_gate.get(
            "bundle_includes_analyst_output_claim"
        ) is True,
        "professional_finding_emitted_count": int(admission.get("professional_finding_emitted_count") or 0),
        "professional_emit_allowed_count": int(claim.get("professional_emit_allowed_count") or 0),
        "professional_emit_allowed": claim.get("professional_emit_allowed") is True,
        "counterexample_pair_count_is_independent_evidence_count": False,
        "provider_success_is_tactical_success_truth": False,
        "comparable_is_same_tactical_situation_truth": False,
        "recurrence_is_intention_truth": False,
        "causal_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }
    (out_dir / OUTPUT_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if acceptance_surface_ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
