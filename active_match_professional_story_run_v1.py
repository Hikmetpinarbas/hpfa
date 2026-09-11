from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import active_match_spine_runner as canonical_runner

MODULE_ID = "active_match_professional_story_run_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
TRUE_ACTION_COUNT = "UNKNOWN"
ACTIVE_MATCH_RELATIVE_PATH = Path("runtime/active_single_match/current")
FULL_SPINE_JSON = "active_match_full_spine_v1.json"
PROCESS_STORY_JSON = "active_match_process_story_sidecar_v1.json"
PROCESS_STORY_TXT = "active_match_process_story_sidecar_v1.txt"
ANALYST_REPORT = "HPFA_ANALYST_REPORT.txt"
BUNDLE_MANIFEST = "HPFA_ACTIVE_MATCH_BUNDLE_MANIFEST.json"
BUNDLE_ZIP = "HPFA_ACTIVE_MATCH_BUNDLE.zip"
BUNDLE_MODULE_ID = "active_match_standard_user_bundle_v1"


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


def _git_worktree_clean(repo_root: Path) -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    return completed.returncode == 0 and not completed.stdout.strip()


def _run_canonical_full_spine(
    *,
    match_dir: Path,
    out_dir: Path,
    repo_root: Path,
    runtime_authority_root: Path,
    expected_product_commit: str | None = None,
) -> dict[str, Any]:
    """Run the existing canonical full-spine with exact product and match authority separated."""
    product_commit = _git_head(repo_root)
    product_worktree_clean = _git_worktree_clean(repo_root)
    expected = str(expected_product_commit or "").strip() or None
    commit_matches_expected = expected is not None and product_commit == expected

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

    provenance_valid = expected is not None and commit_matches_expected and product_worktree_clean
    if not provenance_valid:
        reasons = []
        if expected is None:
            reasons.append("expected_product_commit_required")
        if expected is not None and not commit_matches_expected:
            reasons.append("product_commit_mismatch_or_unavailable")
        if not product_worktree_clean:
            reasons.append("product_worktree_not_clean")
        return {
            "command": command,
            "returncode": 2,
            "passed": False,
            "stdout": "",
            "stderr": ";".join(reasons),
            "product_execution_root": str(repo_root),
            "runtime_authority_root": str(runtime_authority_root),
            "product_commit": product_commit,
            "expected_product_commit": expected,
            "product_commit_matches_expected": commit_matches_expected,
            "product_worktree_clean": product_worktree_clean,
            "exact_head_provenance_verified": False,
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
        "product_worktree_clean": True,
        "exact_head_provenance_verified": True,
        "exact_head_authority_separation_enforced": True,
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _runtime_authority_root(match_dir: Path) -> Path:
    """Return the explicit ACTIVE_MATCH authority root without resolving lexical aliases."""
    suffix = ACTIVE_MATCH_RELATIVE_PATH.parts
    if tuple(match_dir.parts[-len(suffix):]) != tuple(suffix):
        raise ValueError(f"runtime_authority_path_invalid:{match_dir}")
    root = match_dir
    for _ in suffix:
        root = root.parent
    return root


def _bundle_contract_valid(manifest: dict[str, Any]) -> bool:
    if manifest.get("module_id") != BUNDLE_MODULE_ID:
        return False
    required_true = (
        "analyst_text_requires_final_assembly_admission",
        "sequence_lineage_preserved_in_analyst_report",
        "sequence_claim_ceiling_revalidated_in_analyst_report",
        "sequence_null_context_locks_revalidated_in_analyst_report",
        "match_story_lineage_preserved_in_analyst_report",
        "match_story_alternative_explanation_lineage_revalidated_in_analyst_report",
    )
    if any(manifest.get(key) is not True for key in required_true):
        return False
    required_false = (
        "alternative_explanation_is_independent_counterevidence_vote",
        "alternative_explanation_count_is_support_count",
        "current_invocation_artifacts_are_publication_authority",
        "bundle_file_inventory_is_publication_authority",
        "production_release",
    )
    if any(manifest.get(key) is not False for key in required_false):
        return False
    if manifest.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        return False
    if manifest.get("true_action_count") != TRUE_ACTION_COUNT:
        return False
    if manifest.get("process_story_publication_authority_artifact") != PROCESS_STORY_TXT:
        return False
    return True


def _bundle_physical_valid(zip_path: Path) -> bool:
    if not zip_path.is_file() or zip_path.stat().st_size <= 0:
        return False
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            if archive.testzip() is not None:
                return False
            names = set(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return False
    required_members = {
        BUNDLE_MANIFEST,
        ANALYST_REPORT,
        PROCESS_STORY_TXT,
        FULL_SPINE_JSON,
    }
    return required_members.issubset(names)


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run the canonical HPFA ACTIVE_MATCH full Postmatch pipeline and summarize analyst-facing story/bundle activation"
    )
    parser.add_argument("--match-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--expected-product-commit",
        required=True,
        help="Exact checkout commit required for this physical acceptance invocation.",
    )
    args = parser.parse_args()

    # Preserve the lexical match path so canonical authority validation can reject
    # symlink/alias components. Do not resolve it before validation.
    match_dir = Path(args.match_dir).expanduser().absolute()
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
        output_path = out_dir / "active_match_professional_story_run_v1.json"
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    process_story = _load(out_dir / PROCESS_STORY_JSON)
    bundle_manifest = _load(out_dir / BUNDLE_MANIFEST)

    required_artifacts = {
        FULL_SPINE_JSON: (out_dir / FULL_SPINE_JSON).is_file(),
        PROCESS_STORY_JSON: (out_dir / PROCESS_STORY_JSON).is_file(),
        PROCESS_STORY_TXT: (out_dir / PROCESS_STORY_TXT).is_file(),
        ANALYST_REPORT: (out_dir / ANALYST_REPORT).is_file(),
        BUNDLE_MANIFEST: (out_dir / BUNDLE_MANIFEST).is_file(),
        BUNDLE_ZIP: (out_dir / BUNDLE_ZIP).is_file(),
    }
    bundle_contract_valid = _bundle_contract_valid(bundle_manifest)
    bundle_physical_valid = _bundle_physical_valid(out_dir / BUNDLE_ZIP)
    authority_separation_valid = (
        canonical.get("exact_head_authority_separation_enforced") is True
        and canonical.get("product_execution_root") == str(repo_root)
        and canonical.get("runtime_authority_root") == str(runtime_authority_root)
        and repo_root != runtime_authority_root
    )
    exact_product_commit_verified = (
        canonical.get("exact_head_provenance_verified") is True
        and canonical.get("product_commit_matches_expected") is True
        and canonical.get("product_worktree_clean") is True
    )
    required_analysis_layers_activated = (
        canonical["passed"]
        and authority_separation_valid
        and exact_product_commit_verified
        and bool(full_spine)
        and all(required_artifacts.values())
        and bundle_contract_valid
        and bundle_physical_valid
    )

    payload = {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if required_analysis_layers_activated else "FAIL_CLOSED",
        "decision": (
            "ACTIVE_MATCH_CANONICAL_FULL_POSTMATCH_PIPELINE_EVALUATED"
            if required_analysis_layers_activated
            else "ACTIVE_MATCH_CANONICAL_FULL_POSTMATCH_PIPELINE_INCOMPLETE"
        ),
        "canonical_orchestrator": "active_match_spine_runner.py --full-spine",
        "product_code_root": str(repo_root),
        "runtime_authority_root": str(runtime_authority_root),
        "product_code_root_equals_runtime_authority_root": repo_root == runtime_authority_root,
        "product_runtime_authority_separation_valid": authority_separation_valid,
        "product_code_commit": canonical.get("product_commit"),
        "expected_product_commit": canonical.get("expected_product_commit"),
        "product_worktree_clean": canonical.get("product_worktree_clean"),
        "exact_product_commit_verified": exact_product_commit_verified,
        "parallel_runtime_engine_created": False,
        "required_analysis_layers_activated": required_analysis_layers_activated,
        "required_artifacts": required_artifacts,
        "canonical_full_spine_run": canonical,
        "canonical_full_spine_status": full_spine.get("status"),
        "canonical_full_spine_decision": full_spine.get("decision"),
        "process_story_status": process_story.get("status"),
        "process_story_decision": process_story.get("decision"),
        "process_story_runtime_bound": process_story.get("story_path_blocked") is False if process_story else False,
        "story_path_blocked": bool(process_story.get("story_path_blocked", True)) if process_story else True,
        "story_path_block_reason": process_story.get("story_path_block_reason") if process_story else "process_story_artifact_missing",
        "entity_story_count": int(process_story.get("entity_story_count") or 0) if process_story else 0,
        "report_block_count": int(process_story.get("report_block_count") or 0) if process_story else 0,
        "ready_assembly_item_count": int(process_story.get("ready_assembly_item_count") or 0) if process_story else 0,
        "analyst_report_present": required_artifacts[ANALYST_REPORT],
        "bundle_manifest_present": required_artifacts[BUNDLE_MANIFEST],
        "bundle_zip_present": required_artifacts[BUNDLE_ZIP],
        "bundle_contract_valid": bundle_contract_valid,
        "bundle_physical_valid": bundle_physical_valid,
        "bundle_file_inventory_is_publication_authority": False,
        "bundle_presence_is_analysis_activation": False,
        "alternative_explanation_is_independent_counterevidence_vote": False,
        "alternative_explanation_count_is_support_count": False,
        "pipeline_is_possession_truth": False,
        "pipeline_is_tactical_plan_truth": False,
        "professional_story_is_tactical_plan_truth": False,
        "professional_story_is_coach_intention_truth": False,
        "professional_story_is_causality_truth": False,
        "professional_story_is_dominance_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
    }

    output_path = out_dir / "active_match_professional_story_run_v1.json"
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))

    return 0 if required_analysis_layers_activated else 2


if __name__ == "__main__":
    raise SystemExit(main())