from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[5]

CURRENT_AUTHORITY_FILES = [
    REPO_ROOT / "docs/governance/HPFA_MASTER_PROJECT_DIRECTIVE_SHORT_CURRENT.md",
    REPO_ROOT / "docs/governance/HPFA_OPERATOR_HANDOFF_CURRENT.md",
    REPO_ROOT / "docs/governance/HPFA_NEW_OPERATOR_HANDOFF_2026-09-20.md",
    REPO_ROOT / "docs/governance/HPFA_NEW_PAGE_CONTINUITY_HANDOFF_PROMPT_V1.md",
    REPO_ROOT / "docs/governance/HPFA_NORTH_STAR_RECENTERING_PROMPT_V1.md",
    REPO_ROOT / "docs/governance/HPFA_POSITIVE_SCOPE_NARRATIVE_POLICY_V1.md",
]

ACTIVE_HUMAN_PROSE_FILES = [
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/user_output_bundle.py",
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/full_system_match_diagnostic.py",
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/full_system_match_diagnostic_harness.py",
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/rich_multiformat_analysis_lane.py",
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/occurrence_consequence_projection.py",
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/rich_construct_metric_governance_guard.py",
    REPO_ROOT / "hpfa/modules/core/active_match_spine_runner/src/variant_feature_challenge_runtime_binding.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/analyst_output_claim_contract_projection.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/claim_satisfiability_gate.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/safe_finding_occurrence_consequence_burden_adapter.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/safe_sentence_render_completeness.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/comparable_outcome_counterevidence_projection.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/derived_lineage_guard.py",
    REPO_ROOT / "hpfa/modules/core/visible_action_sequence_candidates_lite/src/safe_finding_admission_projection.py",
]

BANNED_PROSE_PATTERNS = [
    r"\bthis is not\b",
    r"\bdoes not prove\b",
    r"\bdoes not establish\b",
    r"\bwithout tracking(?:/video)?\b",
    r"\bwithout video\b",
    r"\bnot automatically\b",
    r"\bwhat must not\b",
    r"\bclaim boundary\b",
    r"\bforbidden inference\b",
    r"\bne söyleyemeyiz\b",
    r"\bdeğildir\b",
    r"\bkanıtlamaz\b",
    r"\bgöstermez\b",
    r"\byapılamaz\b",
    r"\bkullanılamaz\b",
]


def _prose_lines(path: Path) -> list[str]:
    lines = []
    in_fence = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.fullmatch(r"[A-Z0-9_./:=+-]+", stripped):
            continue
        lines.append(raw)
    return lines


def test_current_authority_and_analyst_prose_use_positive_scope_language() -> None:
    failures: list[str] = []
    for path in CURRENT_AUTHORITY_FILES + ACTIVE_HUMAN_PROSE_FILES:
        text = "\n".join(_prose_lines(path))
        for pattern in BANNED_PROSE_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{path.relative_to(REPO_ROOT)}:{line}: {pattern}")
    assert not failures, "Positive-scope narrative policy violations:\n" + "\n".join(failures)


def test_policy_is_linked_from_current_authority() -> None:
    policy_name = "HPFA_POSITIVE_SCOPE_NARRATIVE_POLICY_V1.md"
    linked = 0
    for path in CURRENT_AUTHORITY_FILES[:-1]:
        if policy_name in path.read_text(encoding="utf-8"):
            linked += 1
    assert linked == len(CURRENT_AUTHORITY_FILES) - 1
