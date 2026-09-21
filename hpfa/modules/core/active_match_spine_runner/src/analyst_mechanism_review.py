from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .mechanism_story_review_selector import build_mechanism_story_review_shortlist
except ImportError:  # compatibility for direct src-path test/runtime imports
    from mechanism_story_review_selector import build_mechanism_story_review_shortlist

FEATURE_DELTA_JSON = "grammar_stable_variant_feature_delta_projection_v1.json"
IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"
OCCURRENCE_CONSEQUENCE_JSON = "occurrence_consequence_projection_v1.json"
SEQUENCE_JSON = "visible_action_sequence_candidates_lite_v1.json"
PROCESS_VARIANT_JSON = "observable_process_variant_binding_projection_v1.json"
PROCESS_PARTICIPATION_JSON = "analyst_episode_process_participation_projection_v1.json"
VARIANT_FEATURE_CHALLENGE_JSON = "variant_feature_challenge_projection_v1.json"
ANALYST_OUTPUT_CLAIM_JSON = "analyst_output_claim_contract_projection_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _declared_current(full_spine: dict[str, Any], filename: str) -> bool:
    values = list(full_spine.get("current_invocation_artifacts") or [])
    binding = full_spine.get("variant_feature_challenge_runtime_binding")
    if isinstance(binding, dict) and binding.get("post_sequence_admission_finalized") is True:
        values.extend(binding.get("post_sequence_current_invocation_artifacts") or [])
    for value in values:
        if Path(str(value)).name == filename:
            return True
    return False


def _pretty_key(value: Any) -> str:
    return str(value or "").strip().replace("_", " ").title()


def _team_names(identity_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in identity_payload.get("team_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("team_identity_candidate_id") or "").strip()
        name = str(row.get("team_normalized_key") or "").strip()
        if ref and name:
            result[ref] = _pretty_key(name)
    return result


def _actor_names(identity_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in identity_payload.get("actor_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("actor_identity_candidate_id") or "").strip()
        name = str(row.get("actor_normalized_key") or "").strip()
        if ref and name:
            result[ref] = _pretty_key(name)
    return result


def _grammar_label(tokens: list[Any]) -> str:
    rendered: list[str] = []
    for raw in tokens:
        token = str(raw or "").strip()
        if token.startswith("LAYER[") and token.endswith("]"):
            body = token[6:-1]
            if "|" in body:
                body = " + ".join(part for part in body.split("|") if part)
                body += " (same-time unordered)"
            rendered.append(body)
        elif token:
            rendered.append(token)
    return " -> ".join(rendered) if rendered else "UNRESOLVED_GRAMMAR"


def _feature_row(record: dict[str, Any], token: str) -> dict[str, Any] | None:
    for row in record.get("consequence_feature_difference_candidates") or []:
        if isinstance(row, dict) and str(row.get("feature_token") or "") == token:
            return row
    return None


def _fmt_counts(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    return (
        f"success={int(row.get('success_visible_numerator') or 0)}/"
        f"{int(row.get('success_eligible_denominator') or 0)} "
        f"failure={int(row.get('failure_visible_numerator') or 0)}/"
        f"{int(row.get('failure_eligible_denominator') or 0)}"
    )


def _fmt_clock(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if seconds < 0:
        return "UNKNOWN"
    minute = int(seconds // 60)
    second = int(seconds - minute * 60)
    return f"{minute:02d}:{second:02d}"


def _exact_time_key(value: Any) -> tuple[str, str]:
    """Identity key for one exact visible time candidate; no tolerance/window is used."""
    try:
        return ("NUMERIC", f"{float(value):.9f}")
    except (TypeError, ValueError):
        return ("RAW", str(value))


def _occurrence_spine_lines(root: Path, full_spine: dict[str, Any]) -> list[str]:
    if not _declared_current(full_spine, OCCURRENCE_CONSEQUENCE_JSON):
        return [
            "primary_occurrence_spine=UNAVAILABLE_CURRENT_INVOCATION",
            "surface_role_note=Episode/action-volume adaylari primary action identity sayimi degildir.",
        ]
    payload = _load_json(root / OCCURRENCE_CONSEQUENCE_JSON)
    if not payload or str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return [
            "primary_occurrence_spine=FAIL_CLOSED_OR_UNREADABLE",
            "surface_role_note=Episode/action-volume adaylari primary action identity sayimi degildir.",
        ]
    return [
        "primary_occurrence_spine: "
        f"occurrence_candidates={int(payload.get('occurrence_consequence_projection_count') or 0)} "
        f"visible_consequence_support={int(payload.get('occurrence_with_visible_consequence_support_count') or 0)} "
        f"fully_observed_no_followup={int(payload.get('complete_to_declared_horizon_no_admitted_followup_count') or 0)} "
        f"right_censored={int(payload.get('right_censored_occurrence_count') or 0)} "
        f"unresolved_censoring={int(payload.get('right_censoring_unresolved_occurrence_count') or 0)}",
        "surface_role_note=Primary occurrence spine futbol aksiyon-uyesi aday yuzeyidir; "
        "episode/action-volume ve legacy trace yuzeyleri support/context'tir, canonical action count degildir.",
    ]


def _context_focus_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return non-actor context diagnostics that may justify analyst review.

    These remain descriptive candidates only. Actor identity, provider direction, shot
    annotations and navigation/binding metadata are deliberately excluded so they do not
    become the leading football-mechanism explanation.
    """
    result: list[dict[str, Any]] = []
    for row in record.get("context_feature_difference_candidates") or []:
        if not isinstance(row, dict):
            continue
        token = str(row.get("feature_token") or "")
        if "actor_identity_candidate_ids:" in token:
            continue
        if "process_shot_present_annotation_candidate" in token:
            continue
        if "process_episode_navigation_binding_visible" in token:
            continue
        if "provider_direction_candidates" in token:
            continue
        if "provider_progression_candidates" in token:
            continue
        if "provider_zone_candidates" in token:
            continue
        if "coordinate_derived_zone_candidates" in token:
            continue
        if "process_semantic_role" in token:
            continue
        if any(
            marker in token
            for marker in (
                "process_family_candidate:",
                "occurrence_topology:",
                "required_participant_scope:",
                "binding_state:",
            )
        ):
            result.append(row)
    return result


def _select_context_focus(record: dict[str, Any]) -> dict[str, Any] | None:
    candidates = _context_focus_candidates(record)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: abs(float(item.get("descriptive_rate_delta_success_minus_failure") or 0.0)),
    )


def _actor_locator_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in (record.get("context_feature_difference_candidates") or [])
        if isinstance(row, dict)
        and "actor_identity_candidate_ids:" in str(row.get("feature_token") or "")
    ]


def _select_actor_locator(record: dict[str, Any]) -> dict[str, Any] | None:
    candidates = _actor_locator_candidates(record)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: abs(float(item.get("descriptive_rate_delta_success_minus_failure") or 0.0)),
    )


def _focus_actor_ref(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    token = str(row.get("feature_token") or "")
    if "actor_identity_candidate_ids:" not in token:
        return None
    value = token.rsplit("actor_identity_candidate_ids:", 1)[-1].strip()
    return value or None


def _render_context_focus(row: dict[str, Any] | None) -> str:
    if not row:
        return "NO_NON_ACTOR_CONTEXT_DIAGNOSTIC_EXPOSED"
    token = str(row.get("feature_token") or "")
    label = token
    if "process_family_candidate:" in token:
        family = token.rsplit("process_family_candidate:", 1)[-1]
        label = "process_context_candidate=" + _pretty_key(family)
    elif "occurrence_topology:" in token:
        label = "occurrence_topology=" + _pretty_key(token.rsplit("occurrence_topology:", 1)[-1])
    elif "required_participant_scope:" in token:
        label = "participant_scope=" + _pretty_key(token.rsplit("required_participant_scope:", 1)[-1])
    elif "binding_state:" in token:
        label = "binding_state=" + _pretty_key(token.rsplit("binding_state:", 1)[-1])
    success_n = int(row.get("success_visible_numerator") or 0)
    success_d = int(row.get("success_eligible_denominator") or 0)
    failure_n = int(row.get("failure_visible_numerator") or 0)
    failure_d = int(row.get("failure_eligible_denominator") or 0)
    delta = float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0)
    return (
        f"{label} success={success_n}/{success_d} failure={failure_n}/{failure_d} "
        f"descriptive_rate_delta={delta:+.3f}"
    )


def _context_source_role(row: dict[str, Any] | None) -> str:
    if not row:
        return "NO_CURRENT_CONTEXT_SOURCE_EXPOSED"
    surface = str(row.get("feature_surface_detail") or "").strip()
    if surface == "PROVIDER_REVIEWED_PROCESS_PARTICIPATION_CONTEXT":
        return "PROVIDER_REVIEWED_ANNOTATION"
    return "SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED"


def _render_context_source(row: dict[str, Any] | None) -> str:
    if not row:
        return "source_role=NO_CURRENT_CONTEXT_SOURCE_EXPOSED"
    surface = str(row.get("feature_surface_detail") or "UNDECLARED_SURFACE").strip()
    scope = str(row.get("feature_scope") or "UNDECLARED_SCOPE").strip()
    denominator = str(row.get("eligible_denominator_basis") or "UNDECLARED_DENOMINATOR_BASIS").strip()
    ceiling = str(row.get("claim_ceiling") or "UNDECLARED_CLAIM_CEILING").strip()
    dependency = str(row.get("dependency_independence_proven") is True).lower()
    statistical = str(row.get("statistical_independence_proven") is True).lower()
    return (
        f"source_role={_context_source_role(row)} surface={surface} scope={scope} "
        f"denominator_basis={denominator} claim_ceiling={ceiling} "
        f"dependency_independence_proven={dependency} statistical_independence_proven={statistical}"
    )


def _render_actor_locator(row: dict[str, Any] | None, actors: dict[str, str]) -> str:
    if not row:
        return "NO_ACTOR_LOCATOR_CONTRAST_EXPOSED"
    token = str(row.get("feature_token") or "")
    actor_ref = token.rsplit("actor_identity_candidate_ids:", 1)[-1].strip()
    label = actors.get(actor_ref, actor_ref)
    success_n = int(row.get("success_visible_numerator") or 0)
    success_d = int(row.get("success_eligible_denominator") or 0)
    failure_n = int(row.get("failure_visible_numerator") or 0)
    failure_d = int(row.get("failure_eligible_denominator") or 0)
    delta = float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0)
    return (
        f"actor={label} success={success_n}/{success_d} failure={failure_n}/{failure_d} "
        f"descriptive_rate_delta={delta:+.3f} role=VIDEO_REVIEW_LOCATOR_ONLY"
    )


def _family_sequence_refs(
    record: dict[str, Any],
    process_variant_payload: dict[str, Any],
    sequence_payload: dict[str, Any],
) -> set[str]:
    family_ref = str(record.get("source_process_variant_family_ref") or "").strip()
    if not family_ref:
        return set()
    family = next(
        (
            row
            for row in process_variant_payload.get("observable_process_variant_families") or []
            if isinstance(row, dict) and str(row.get("observable_process_variant_family_id") or "") == family_ref
        ),
        None,
    )
    if not isinstance(family, dict):
        return set()
    variant_by_ref = {
        str(row.get("partial_order_occurrence_variant_id") or ""): row
        for row in sequence_payload.get("partial_order_occurrence_variants") or []
        if isinstance(row, dict)
    }
    result: set[str] = set()
    for variant_ref in family.get("member_variant_refs") or []:
        variant = variant_by_ref.get(str(variant_ref))
        if not isinstance(variant, dict):
            continue
        sequence_ref = str(variant.get("sequence_ref") or "").strip()
        if sequence_ref:
            result.add(sequence_ref)
    return result


def _clip_locator_lines(
    record: dict[str, Any],
    focus_actor_ref: str | None,
    actors: dict[str, str],
    sequence_payload: dict[str, Any],
    process_variant_payload: dict[str, Any],
    *,
    limit: int = 3,
) -> list[str]:
    if not focus_actor_ref or not sequence_payload or not process_variant_payload:
        return []
    family_sequence_refs = _family_sequence_refs(record, process_variant_payload, sequence_payload)
    if not family_sequence_refs:
        return []
    team_refs = {str(value) for value in record.get("team_identity_candidate_ids") or [] if str(value)}
    periods = {str(value) for value in record.get("period_candidates") or [] if str(value)}
    best_by_focus_time: dict[tuple[str, str], tuple[int, float, str]] = {}

    for divergence in sequence_payload.get("first_supported_branch_divergence_candidates") or []:
        if not isinstance(divergence, dict):
            continue
        if str(divergence.get("team_identity_candidate_id") or "") not in team_refs:
            continue
        if str(divergence.get("period_candidate") or "") not in periods:
            continue

        family_profiles_raw: list[tuple[str, Any, str, str]] = []
        for branch in divergence.get("branch_profiles") or []:
            if not isinstance(branch, dict):
                continue
            branch_refs = {str(value) for value in branch.get("supporting_visible_sequence_candidate_ids") or []}
            if not (branch_refs & family_sequence_refs):
                continue
            outcome = str(branch.get("branch_outcome_state") or "UNRESOLVED")
            neighbor_time = branch.get("neighbor_time_candidate")
            for semantic in branch.get("semantic_profiles") or []:
                if not isinstance(semantic, dict):
                    continue
                actor_ref = str(semantic.get("actor_identity_candidate_id") or "").strip()
                family = str(semantic.get("primary_family_candidate") or "UNRESOLVED")
                family_profiles_raw.append((outcome, neighbor_time, actor_ref, family))

        seen_profiles: set[tuple[str, tuple[str, str], str, str]] = set()
        family_profiles: list[tuple[str, Any, str, str]] = []
        for outcome, time_value, actor_ref, family in family_profiles_raw:
            key = (outcome, _exact_time_key(time_value), actor_ref, family)
            if key in seen_profiles:
                continue
            seen_profiles.add(key)
            family_profiles.append((outcome, time_value, actor_ref, family))

        outcome_states = {item[0] for item in family_profiles if item[0]}
        if len(outcome_states) < 2:
            continue

        focus_times: dict[tuple[str, str], Any] = {}
        for _outcome, time_value, actor_ref, _family in family_profiles:
            if actor_ref == focus_actor_ref:
                focus_times.setdefault(_exact_time_key(time_value), time_value)
        if not focus_times:
            continue

        anchor_time_raw = divergence.get("shared_anchor_time_candidate")
        try:
            anchor_sort = float(anchor_time_raw)
        except (TypeError, ValueError):
            anchor_sort = float("inf")
        branch_text = "; ".join(
            f"{_fmt_clock(time_value)} {actors.get(actor_ref, actor_ref or 'UNRESOLVED_ACTOR')} "
            f"{outcome.replace('_SEMANTIC_VISIBLE', '')} {family}"
            for outcome, time_value, actor_ref, family in family_profiles
        )
        rendered = f"shared_anchor={_fmt_clock(anchor_time_raw)} -> {branch_text}"
        richness = len(family_profiles)

        for focus_key in focus_times:
            current = best_by_focus_time.get(focus_key)
            candidate = (richness, anchor_sort, rendered)
            if current is None or richness > current[0] or (richness == current[0] and anchor_sort < current[1]):
                best_by_focus_time[focus_key] = candidate

    if not best_by_focus_time:
        return []
    selected = sorted(best_by_focus_time.values(), key=lambda item: item[1])
    result: list[str] = []
    seen_rendered: set[str] = set()
    for _richness, _anchor, rendered in selected:
        if rendered in seen_rendered:
            continue
        seen_rendered.add(rendered)
        result.append(rendered)
        if len(result) >= limit:
            break
    return result


def build_mechanism_review_lines(
    output_root: str | Path,
    full_spine: dict[str, Any],
) -> list[str]:
    """Render current grammar-stable process differences for analyst review only."""
    root = Path(output_root)
    if not _declared_current(full_spine, FEATURE_DELTA_JSON):
        return ["- Current invocation process-difference surface mevcut degil; eski artifact kullanilmadi."]

    payload = _load_json(root / FEATURE_DELTA_JSON)
    if not payload or str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return ["- Process-difference surface fail-closed veya okunamadi; mekanizma adayi uretilmedi."]

    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    sequence_payload = _load_json(root / SEQUENCE_JSON) if _declared_current(full_spine, SEQUENCE_JSON) else {}
    process_variant_payload = (
        _load_json(root / PROCESS_VARIANT_JSON) if _declared_current(full_spine, PROCESS_VARIANT_JSON) else {}
    )
    process_participation_payload = (
        _load_json(root / PROCESS_PARTICIPATION_JSON)
        if _declared_current(full_spine, PROCESS_PARTICIPATION_JSON)
        else {}
    )
    variant_feature_challenge_payload = (
        _load_json(root / VARIANT_FEATURE_CHALLENGE_JSON)
        if _declared_current(full_spine, VARIANT_FEATURE_CHALLENGE_JSON)
        else {}
    )
    teams = _team_names(identity)
    actors = _actor_names(identity)
    records = [
        row for row in (payload.get("grammar_stable_variant_feature_delta_records") or [])
        if isinstance(row, dict)
    ]
    if not records:
        return ["- Bu run'da grammar-stable visible-outcome variation ailesi gorunmedi."]

    analyst_output_payload = (
        _load_json(root / ANALYST_OUTPUT_CLAIM_JSON)
        if _declared_current(full_spine, ANALYST_OUTPUT_CLAIM_JSON)
        else {}
    )
    shortlist = build_mechanism_story_review_shortlist(
        payload,
        analyst_output_claim_payload=analyst_output_payload or None,
        process_variant_payload=process_variant_payload or None,
        process_participation_payload=process_participation_payload or None,
        variant_feature_challenge_payload=variant_feature_challenge_payload or None,
        limit=5,
    )

    lines = [
        "Bu bolum YAYINLANABILIR BULGU degildir; analyst-review mekanizma adayidir.",
        f"story_shortlist_status={shortlist.get('status')}",
        f"story_shortlist_count={int(shortlist.get('shortlist_count') or 0)}",
        f"story_bounded_review_only_count={int(shortlist.get('bounded_review_only_count') or 0)}",
        "story_selection_is_truth_ranking=false",
        "story_selection_is_confidence_score=false",
        "story_selection_can_authorize_emit=false",
        "Adaylar siralanmamistir. Oranlar gercek basari olasiligi degildir ve causality/tactical-plan kaniti sayilmaz.",
        *_occurrence_spine_lines(root, full_spine),
        "information_value_guard=actor identity yalniz locator; same-team continuation/opponent handover outcome-adjacent descriptive consequence; process-context farki review adayi olabilir ama mekanizma/taktik/neden truth degildir.",
        "source_provenance_guard=provider-reviewed annotation direct admitted observation degildir; derived context physical/tracking truth degildir; unresolved source role yorumlama izni vermez.",
        "locator_semantics=FIRST_SUCCESSOR_AFTER_SHARED_VISIBLE_ANCHOR_NOT_PROVEN_FIRST_DIVERGENCE",
    ]
    for row in shortlist.get("shortlist") or []:
        if not isinstance(row, dict):
            continue
        eligibility = str(row.get("story_eligibility_state") or "UNRESOLVED")
        family_ref = str(row.get("source_process_variant_family_ref") or "UNRESOLVED")
        lower = row.get("rate_bound_lower")
        upper = row.get("rate_bound_upper")
        if eligibility == "BOUND_AWARE_REVIEW_ONLY" and lower is not None and upper is not None:
            lines.append(
                "story_review_shortlist: "
                f"family={family_ref} eligibility={eligibility} "
                f"visible_outcome_rate_bound={float(lower):.6f}-{float(upper):.6f} "
                "confidence_interval=false probability=false emit=false"
            )
        else:
            lines.append(
                "story_review_shortlist: "
                f"family={family_ref} eligibility={eligibility} "
                "emit=false truth_ranking=false"
            )

    shortlisted_refs = {
        str(row.get("source_mechanism_review_ref") or "")
        for row in (shortlist.get("shortlist") or [])
        if isinstance(row, dict) and row.get("source_mechanism_review_ref")
    }
    shortlist_support_by_ref = {
        str(row.get("source_mechanism_review_ref") or ""): row
        for row in (shortlist.get("shortlist") or [])
        if isinstance(row, dict) and row.get("source_mechanism_review_ref")
    }
    shortlisted_signatures = {
        (
            tuple(str(v) for v in (row.get("team_identity_candidate_ids") or [])),
            tuple(str(v) for v in (row.get("period_candidates") or [])),
            tuple(str(v) for v in (row.get("grammar_signature_tokens") or [])),
            int(row.get("resolved_variant_count") or 0),
            int(row.get("success_resolved_variant_count") or 0),
            int(row.get("failure_resolved_variant_count") or 0),
        )
        for row in (shortlist.get("shortlist") or [])
        if isinstance(row, dict) and not row.get("source_mechanism_review_ref")
    }
    review_records = [
        record for record in records
        if (
            str(record.get("grammar_stable_variant_feature_delta_id") or "") in shortlisted_refs
            or (
                not record.get("grammar_stable_variant_feature_delta_id")
                and (
                    tuple(str(v) for v in (record.get("team_identity_candidate_ids") or [])),
                    tuple(str(v) for v in (record.get("period_candidates") or [])),
                    tuple(str(v) for v in (record.get("grammar_signature_tokens") or [])),
                    int(record.get("resolved_variant_count") or 0),
                    int(record.get("success_resolved_variant_count") or 0),
                    int(record.get("failure_resolved_variant_count") or 0),
                ) in shortlisted_signatures
            )
        )
    ]
    lines.append(
        f"story_detail_render_count={len(review_records)} source_candidate_count={len(records)}"
    )
    lines.append(
        "story_detail_render_scope=SHORTLIST_ONLY_ATTENTION_COMPRESSION_NOT_EVIDENCE_REMOVAL"
    )

    for index, record in enumerate(review_records, start=1):
        team_ids = [str(value) for value in (record.get("team_identity_candidate_ids") or []) if str(value)]
        team = ", ".join(teams.get(value, value) for value in team_ids) or "UNRESOLVED_TEAM"
        periods = ",".join(str(value) for value in (record.get("period_candidates") or [])) or "UNKNOWN"
        grammar = _grammar_label(list(record.get("grammar_signature_tokens") or []))
        resolved = int(record.get("resolved_variant_count") or 0)
        success = int(record.get("success_resolved_variant_count") or 0)
        failure = int(record.get("failure_resolved_variant_count") or 0)
        first_consequence_layer = record.get("first_supported_consequence_difference_layer_candidate")
        first_context_layer = record.get("first_supported_context_difference_layer_candidate")
        context_missing = int(
            record.get("context_coverage_incomplete_variant_count")
            or record.get("process_context_coverage_incomplete_variant_count")
            or 0
        )
        right_censored = int(record.get("right_censored_variant_count") or 0)

        lines.append(
            f"- M{index} | {team} | period={periods} | grammar={grammar} | "
            f"resolved={resolved} (SUCCESS={success}, FAILURE={failure})"
        )
        lines.append(
            f"  first_visible_difference: context_layer={first_context_layer} consequence_layer={first_consequence_layer}"
        )
        shortlist_support = shortlist_support_by_ref.get(
            str(record.get("grammar_stable_variant_feature_delta_id") or ""), {}
        )
        review_support_state = str(
            shortlist_support.get("review_support_state")
            or record.get("review_support_state")
            or ""
        ).strip()
        visible_episode_spread = int(record.get("visible_episode_spread_count") or 0)
        occurrence_disjoint_clusters = int(record.get("occurrence_disjoint_support_cluster_count") or 0)
        if review_support_state or visible_episode_spread or occurrence_disjoint_clusters:
            lines.append(
                "  review_support_scope: "
                f"state={review_support_state or 'UNRESOLVED'} "
                f"visible_episode_spread={visible_episode_spread} "
                f"occurrence_disjoint_clusters={occurrence_disjoint_clusters} "
                "independent_support=false recurrence_truth=false attention_compression_only=true"
            )
        process_context_state = str(
            shortlist_support.get("process_context_binding_state")
            or "UNRESOLVED_NO_SOURCE_BOUND_PROCESS_CONTEXT"
        )
        process_context_counts = dict(
            shortlist_support.get("process_family_episode_presence_counts") or {}
        )
        lines.append(
            "  process_context_binding: "
            f"state={process_context_state} "
            f"visible_episode_count={int(shortlist_support.get('process_context_visible_episode_count') or 0)} "
            f"bound_episode_count={int(shortlist_support.get('process_context_bound_episode_count') or 0)} "
            f"ambiguous_episode_count={int(shortlist_support.get('process_context_ambiguous_episode_count') or 0)} "
            f"family_episode_presence={json.dumps(process_context_counts, sort_keys=True)} "
            f"single_family={shortlist_support.get('single_process_family_candidate') or 'NONE'} "
            "process_identity_truth=false tactical_truth=false causal_truth=false "
            "independent_support=false emit=false"
        )
        challenge_n = int(shortlist_support.get("mechanism_challenge_record_count") or 0)
        if challenge_n:
            lines.append(
                "  mechanism_challenge: "
                f"state={shortlist_support.get('mechanism_challenge_binding_state')} "
                f"record_count={challenge_n} "
                f"feature_surface_counts={json.dumps(shortlist_support.get('mechanism_challenge_feature_surface_counts') or {}, sort_keys=True)} "
                f"reasons={json.dumps(shortlist_support.get('mechanism_challenge_reason_codes') or [])} "
                f"counter_scenarios={json.dumps(shortlist_support.get('mechanism_counter_scenario_candidates') or [])} "
                f"withdrawal_conditions={json.dumps(shortlist_support.get('mechanism_withdrawal_conditions') or [])} "
                "independent_evidence=false counterfactual_truth=false causal_explanation=false emit=false"
            )
        divergence_refs = [
            str(value)
            for value in (record.get("supported_branch_divergence_refs") or [])
            if str(value)
        ]
        success_failure_divergence_refs = [
            str(value)
            for value in (record.get("success_failure_supported_branch_divergence_refs") or [])
            if str(value)
        ]
        if divergence_refs:
            lines.append(
                "  supported_branch_divergence_trace: "
                f"bound={len(divergence_refs)} success_failure_visible={len(success_failure_divergence_refs)} "
                "semantics=FIRST_SUCCESSOR_AFTER_SHARED_VISIBLE_ANCHOR_NOT_PHYSICAL_FIRST_DIVERGENCE "
                "cause=false tactical_truth=false independent_support=false"
            )

        facts = [
            ("same_team_continuation", "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE"),
            ("opponent_handover", "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"),
            ("no_visible_followup", "LAYER[1]::followup_observation_status:NO_VISIBLE_FOLLOWUP"),
            ("process_state_unresolved", "LAYER[1]::process_continuation_status:PROCESS_STATE_UNRESOLVED"),
        ]
        rendered_facts = []
        for label, token in facts:
            counts = _fmt_counts(_feature_row(record, token))
            if counts:
                rendered_facts.append(f"{label} {counts}")
        if rendered_facts:
            lines.append("  outcome_adjacent_consequence_contrast: " + " | ".join(rendered_facts))

        context_focus = _select_context_focus(record)
        actor_locator = _select_actor_locator(record)
        focus_actor_ref = _focus_actor_ref(actor_locator)
        lines.append("  mechanism_context_review_focus: " + _render_context_focus(context_focus))
        lines.append("  mechanism_context_source: " + _render_context_source(context_focus))
        provider_cue = _select_provider_semantic_review_cue(record)
        lines.append("  provider_semantic_context_review_cue: " + _render_provider_semantic_review_cue(provider_cue))
        lines.append("  provider_semantic_context_source: " + _render_provider_semantic_source(provider_cue))
        lines.append("  provider_semantic_context_guard: " + _render_provider_semantic_guard(provider_cue))
        lines.append("  actor_locator_only: " + _render_actor_locator(actor_locator, actors))
        locators = _clip_locator_lines(
            record,
            focus_actor_ref,
            actors,
            sequence_payload,
            process_variant_payload,
        )
        for locator in locators:
            lines.append("  video_review_locator: " + locator)
        lines.append(
            f"  uncertainty: context_missing={context_missing}/{resolved} "
            f"right_censored={right_censored}/{resolved} dependency_independence_proven="
            f"{str(record.get('dependency_independence_proven') is True).lower()}"
        )
        lines.append(
            "  analyst_meaning: Once non-actor process/context farkini, onun source/provenance rolunu ve actor locator ile ilgili klipleri videoda kontrol et. "
            "Actor farkini oyuncu kalitesi/mekanizma; continuation-handover farkini neden/taktik plan; provider labelini fiziksel futbol truth olarak yorumlama."
        )

    record_by_ref = {
        str(record.get("grammar_stable_variant_feature_delta_id") or ""): record
        for record in records
        if record.get("grammar_stable_variant_feature_delta_id")
    }
    grammar_context_groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for selected_row in shortlist.get("shortlist") or []:
        if not isinstance(selected_row, dict):
            continue
        grammar_key = tuple(str(value) for value in (selected_row.get("grammar_signature_tokens") or []))
        if not grammar_key:
            continue
        companions = [
            record_by_ref[ref]
            for ref in (selected_row.get("same_grammar_context_review_refs") or [])
            if ref in record_by_ref
        ]
        if companions:
            grammar_context_groups[grammar_key] = companions
    for grammar_key, context_records in sorted(grammar_context_groups.items()):
        context_keys = {
            (
                tuple(str(v) for v in (record.get("team_identity_candidate_ids") or [])),
                tuple(str(v) for v in (record.get("period_candidates") or [])),
            )
            for record in context_records
        }
        if len(context_keys) < 2:
            continue
        lines.append(
            "same_grammar_context_comparison: "
            f"grammar={_grammar_label(list(grammar_key))} eligible_contexts={len(context_keys)} "
            "scope=SELECTED_GRAMMAR_ELIGIBLE_CONTEXTS_NOT_ALL_MATCH_CONTEXTS "
            "semantics=MATCH_LOCAL_VISIBLE_CONTEXT_COMPARISON_ONLY "
            "tactical_change=false team_quality=false causality=false significance=false"
        )
        for record in sorted(
            context_records,
            key=lambda row: (
                tuple(str(v) for v in (row.get("team_identity_candidate_ids") or [])),
                tuple(str(v) for v in (row.get("period_candidates") or [])),
            ),
        ):
            team_ids = [
                str(value) for value in (record.get("team_identity_candidate_ids") or []) if str(value)
            ]
            team = ", ".join(teams.get(value, value) for value in team_ids) or "UNRESOLVED_TEAM"
            periods = ",".join(str(value) for value in (record.get("period_candidates") or [])) or "UNKNOWN"
            lines.append(
                "  same_grammar_context: "
                f"team={team} period={periods} "
                f"resolved={int(record.get('resolved_variant_count') or 0)} "
                f"success_visible={int(record.get('success_resolved_variant_count') or 0)} "
                f"failure_visible={int(record.get('failure_resolved_variant_count') or 0)} "
                f"visible_episode_spread={int(record.get('visible_episode_spread_count') or 0)} "
                f"occurrence_disjoint_clusters={int(record.get('occurrence_disjoint_support_cluster_count') or 0)} "
                f"success_failure_divergence={int(record.get('success_failure_supported_branch_divergence_count') or 0)} "
                "independent_support=false recurrence_truth=false"
            )

    lines.extend([
        "analyst_action=VIDEO_OR_MATCH_REVIEW_OF_CONTEXT_ENRICHED_VISIBLE_DIFFERENCE_CANDIDATES",
        "claim_ceiling=ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY",
        "professional_emit_allowed=false",
    ])
    return lines


_BASE_BUILD_MECHANISM_REVIEW_LINES = build_mechanism_review_lines


def _base_context_provenance_by_token(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("feature_token") or "").strip(): row
        for row in (record.get("base_context_feature_provenance_records") or [])
        if isinstance(row, dict) and str(row.get("feature_token") or "").strip()
    }


def _provider_semantic_review_candidates(record: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    provenance = _base_context_provenance_by_token(record)
    result: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in record.get("context_feature_difference_candidates") or []:
        if not isinstance(row, dict):
            continue
        token = str(row.get("feature_token") or "").strip()
        source = provenance.get(token)
        if not source:
            continue
        if source.get("feature_information_role") != "PROVIDER_SEMANTIC_CONTEXT_CANDIDATE_ONLY":
            continue
        result.append((row, source))
    return result


def _select_provider_semantic_review_cue(
    record: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    candidates = _provider_semantic_review_candidates(record)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda pair: abs(float(pair[0].get("descriptive_rate_delta_success_minus_failure") or 0.0)),
    )


def _provider_semantic_label(token: str) -> str:
    layer = ""
    body = token
    if token.startswith("LAYER[") and "::" in token:
        layer, body = token.split("::", 1)
        layer += "::"
    field, _, value = body.partition(":")
    field_label = {
        "provider_context_candidates": "provider_context",
        "provider_direction_candidates": "provider_direction",
        "provider_progression_candidates": "provider_progression",
        "provider_zone_candidates": "provider_zone",
    }.get(field, field or "provider_semantic")
    return f"{layer}{field_label}={value or 'UNRESOLVED'}"


def _render_provider_semantic_review_cue(
    cue: tuple[dict[str, Any], dict[str, Any]] | None,
) -> str:
    if not cue:
        return "NO_PROVIDER_SEMANTIC_CONTEXT_CUE_EXPOSED"
    row, _source = cue
    token = str(row.get("feature_token") or "").strip()
    success_n = int(row.get("success_visible_numerator") or 0)
    success_d = int(row.get("success_eligible_denominator") or 0)
    failure_n = int(row.get("failure_visible_numerator") or 0)
    failure_d = int(row.get("failure_eligible_denominator") or 0)
    delta = float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0)
    return (
        f"{_provider_semantic_label(token)} success={success_n}/{success_d} "
        f"failure={failure_n}/{failure_d} descriptive_rate_delta={delta:+.3f} "
        "role=PROVIDER_SEMANTIC_REVIEW_CUE_ONLY "
        "selection=MAX_ABS_DESCRIPTIVE_RATE_DELTA_NOT_STRENGTH_OR_SIGNIFICANCE"
    )


def _render_provider_semantic_source(
    cue: tuple[dict[str, Any], dict[str, Any]] | None,
) -> str:
    if not cue:
        return "source_role=NO_PROVIDER_SEMANTIC_CONTEXT_SOURCE_EXPOSED"
    _row, source = cue
    return (
        f"source_role={source.get('feature_information_role') or 'SOURCE_ROLE_UNRESOLVED_REVIEW_REQUIRED'} "
        f"source_surface={source.get('feature_source_surface') or 'UNRESOLVED_SOURCE_SURFACE'} "
        f"dependency_surface={source.get('feature_dependency_surface') or 'UNRESOLVED_DEPENDENCY_SURFACE'} "
        f"source_field={source.get('feature_source_field') or 'UNRESOLVED_SOURCE_FIELD'} "
        f"denominator_basis={source.get('eligible_denominator_basis') or 'UNRESOLVED_DENOMINATOR_BASIS'} "
        f"claim_ceiling={source.get('claim_ceiling') or 'UNRESOLVED_CLAIM_CEILING'} "
        f"dependency_independence_proven={str(source.get('dependency_independence_proven') is True).lower()} "
        f"statistical_independence_proven={str(source.get('statistical_independence_proven') is True).lower()}"
    )


def _render_provider_semantic_guard(
    cue: tuple[dict[str, Any], dict[str, Any]] | None,
) -> str:
    if not cue:
        return "NOT_APPLICABLE_NO_PROVIDER_SEMANTIC_CONTEXT_CUE"
    _row, source = cue
    return (
        f"physical_geometry_truth={str(source.get('feature_is_physical_geometry_truth') is True).lower()} "
        f"tracking_truth={str(source.get('feature_is_tracking_truth') is True).lower()} "
        f"tactical_truth={str(source.get('feature_is_tactical_truth') is True).lower()} "
        f"causal_truth={str(source.get('feature_is_causal_truth') is True).lower()} "
        "success_probability_truth=false independent_evidence_vote=false "
        "analyst_action=REVIEW_PROVIDER_SEMANTIC_LABEL_AGAINST_MATCH_EVIDENCE"
    )


def build_mechanism_review_lines(
    output_root: str | Path,
    full_spine: dict[str, Any],
) -> list[str]:
    return _BASE_BUILD_MECHANISM_REVIEW_LINES(output_root, full_spine)
