from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

POLICY_FILE = "release/commercial_pilot_policy_v1.json"
BUNDLE_POLICY_FILE = "release/release_bundle_policy_v1.json"
EVIDENCE_FILES = {
    "physical": "physical_acceptance.json",
    "portability": "portability_acceptance.json",
    "bundle": "bundle_integrity.json",
    "installation": "installation_smoke.json",
    "human": "human_report_review.json",
    "red_team": "red_team_review.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(repo: Path, evidence_dir: Path, *, expected_head: str) -> dict[str, Any]:
    policy = _read_json(repo / POLICY_FILE)
    bundle_policy = _read_json(repo / BUNDLE_POLICY_FILE)
    evidence = {
        key: _read_json(evidence_dir / filename)
        for key, filename in EVIDENCE_FILES.items()
    }

    blockers: list[str] = []
    heads = [str(payload.get("exact_head_sha") or "") for payload in evidence.values()]
    exact_head_consistent = bool(expected_head) and all(head == expected_head for head in heads)
    if not exact_head_consistent:
        blockers.append("exact_head_mismatch")

    physical = evidence["physical"]
    if (
        physical.get("execution_exit_code") != 0
        or physical.get("hard_block_count") not in (0, None)
        or physical.get("production_release") is not False
        or physical.get("canonical_event_count") != "UNKNOWN"
        or physical.get("true_action_count") != "UNKNOWN"
    ):
        blockers.append("physical_acceptance_failed")

    portability = evidence["portability"]
    if (
        portability.get("required_profile_count") != 3
        or portability.get("passed_profile_count") != 3
        or portability.get("all_exit_zero") is not True
        or portability.get("production_release") is not False
    ):
        blockers.append("portability_acceptance_failed")

    bundle = evidence["bundle"]
    bundle_integrity_verified = (
        bundle.get("bundle_status") == "PASS"
        and bundle.get("deterministic_bundle") is True
        and bundle.get("forbidden_entry_count") == 0
        and bundle.get("raw_match_data_bundled") is False
        and bundle.get("raw_donor_bundled") is False
    )
    if not bundle_integrity_verified:
        blockers.append("bundle_integrity_failed")

    installation = evidence["installation"]
    isolated_installation_smoke_verified = (
        installation.get("smoke_status") == "PASS"
        and installation.get("isolated_environment") is True
        and installation.get("base_runtime_dependency_count") == 0
    )
    if not isolated_installation_smoke_verified:
        blockers.append("installation_smoke_failed")

    human = evidence["human"]
    if (
        human.get("review_status") != "PASS"
        or human.get("claim_boundary_visible") is not True
        or human.get("evidence_completeness_visible") is not True
        or human.get("zero_emit_not_promoted") is not True
    ):
        blockers.append("human_report_claim_boundary_failed")

    red_team = evidence["red_team"]
    critical_blocker_count = int(red_team.get("critical_blocker_count") or 0)
    if red_team.get("review_status") != "PASS" or critical_blocker_count != 0:
        blockers.append("red_team_failed")

    if policy.get("commercial_distribution_authorized") is not True:
        blockers.append("commercial_distribution_not_authorized")
    if policy.get("commercial_scope") != "ASSISTED_CONTROLLED_PILOT":
        blockers.append("commercial_scope_invalid")
    if policy.get("production_release") is not False:
        blockers.append("production_release_must_remain_false")
    if policy.get("public_index_upload_authorized") is not False:
        blockers.append("public_index_upload_must_remain_false")
    if policy.get("claim_ceiling_may_not_be_strengthened_for_sale") is not True:
        blockers.append("sale_claim_ceiling_guard_missing")
    if policy.get("raw_match_data_bundling_allowed") is not False:
        blockers.append("raw_match_data_bundling_forbidden")
    if policy.get("raw_donor_bundling_allowed") is not False:
        blockers.append("raw_donor_bundling_forbidden")
    if policy.get("third_party_runtime_bundling_allowed") is not False:
        blockers.append("third_party_runtime_bundling_forbidden")

    if bundle_policy.get("match_data_bundling_allowed") is not False:
        blockers.append("bundle_policy_match_data_risk")
    if bundle_policy.get("raw_donor_bundling_allowed") is not False:
        blockers.append("bundle_policy_donor_risk")

    blockers = sorted(set(blockers))
    decision = "CONTROLLED_COMMERCIAL_PILOT_READY" if not blockers else "REVIEW_REQUIRED"

    return {
        "audit_id": "hpfa_commercial_pilot_readiness_v1",
        "decision": decision,
        "exact_head_sha": expected_head,
        "exact_head_consistent": exact_head_consistent,
        "commercial_distribution_authorized": bool(policy.get("commercial_distribution_authorized")),
        "commercial_scope": policy.get("commercial_scope"),
        "production_release": False,
        "public_index_upload_authorized": False,
        "raw_match_data_bundling_allowed": False,
        "raw_donor_bundling_allowed": False,
        "third_party_runtime_bundling_allowed": False,
        "customer_or_provider_authorized_match_data_required": True,
        "critical_blocker_count": critical_blocker_count,
        "bundle_integrity_verified": bundle_integrity_verified,
        "isolated_installation_smoke_verified": isolated_installation_smoke_verified,
        "blockers": blockers,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "claim_ceiling_may_not_be_strengthened_for_sale": True,
        "notes": [
            "Controlled commercial pilot readiness is not PRODUCTION_RELEASE.",
            "Public package-index upload remains unauthorized.",
            "Raw provider data and donor/vendor source remain outside the commercial software bundle.",
            "Zero professional emit is a valid governed outcome and must not be promoted by presentation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    evidence_dir = Path(args.evidence_dir).resolve()
    report = audit(repo, evidence_dir, expected_head=args.expected_head)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["decision"] == "CONTROLLED_COMMERCIAL_PILOT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
