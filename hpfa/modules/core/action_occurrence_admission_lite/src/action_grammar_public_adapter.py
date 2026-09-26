from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from hpfa.modules.core.action_occurrence_admission_lite.src.goal_kick_restart_pass_grammar import (
    bind_goal_kick_restart_pass_grammar,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.intra_actor_action_grammar import (
    build_intra_actor_action_grammar_candidates,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.observation_occurrence_cardinality import (
    bind_observation_occurrence_cardinality,
)
from hpfa.modules.core.action_occurrence_admission_lite.src.single_action_anchor_admission import (
    build_single_action_anchor_candidates,
)


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


CANONICAL_FOOTBALL_GRAMMAR_PATH = (
    Path(__file__).resolve().parents[5] / "canon" / "football_action_process_grammar_v1.json"
)


def load_canonical_football_grammar_registry() -> dict[str, Any]:
    """Load the provider-independent HPFA football grammar registry.

    This registry is semantic reference authority only. Loading or resolving a
    concept never admits an occurrence, never creates event identity, and never
    raises a metric/model output to football truth.
    """
    payload = json.loads(CANONICAL_FOOTBALL_GRAMMAR_PATH.read_text(encoding="utf-8"))
    if payload.get("registry_id") != "hpfa_football_action_process_grammar_v1":
        raise ValueError("unexpected_canonical_football_grammar_registry")
    return payload


def resolve_canonical_football_concept(value: Any) -> dict[str, Any] | None:
    """Resolve a canonical ID or declared alias to one grammar concept.

    Provider raw labels must first pass their provider semantic mapping layer; this
    resolver is intentionally not a fuzzy provider-label normalizer.
    """
    token = _clean(value).upper()
    if not token:
        return None
    matches: list[dict[str, Any]] = []
    for row in load_canonical_football_grammar_registry().get("entries") or []:
        if not isinstance(row, dict):
            continue
        identifiers = {_clean(row.get("id")).upper()}
        identifiers.update(_clean(v).upper() for v in (row.get("aliases") or []) if _clean(v))
        if token in identifiers:
            matches.append(row)
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(f"ambiguous_canonical_football_concept:{token}")
    return copy.deepcopy(matches[0])


REVIEWED_SEMANTIC_RULE_CANONICAL_CONCEPTS = {
    "plvs_v2_shots_saved": "GK_SAVE",
}


def _canonical_family_tokens(candidate: dict[str, Any]) -> list[tuple[str, str]]:
    """Return already-admitted semantic tokens in deterministic precedence.

    Raw provider labels are never interpreted here. Specific canonical subtypes
    may come only from already-admitted structured semantics (for example an exact
    goal-kick restart type) or from an explicitly reviewed HPFA semantic-rule ID.
    A generic container family is suppressed when a more specific admitted concept
    in the same canonical family is available.
    """
    specific: list[tuple[str, str]] = []

    interaction_type = _clean(candidate.get("interaction_type"))
    attributes = candidate.get("attributes")
    if (
        interaction_type == "GOAL_KICK_RESTART_PASS_SEMANTIC_CANDIDATE"
        and isinstance(attributes, dict)
    ):
        restart_type = _clean(attributes.get("restart_type_candidate"))
        if restart_type:
            specific.append(("attributes.restart_type_candidate", restart_type))

    for semantic_rule_id in candidate.get("supporting_semantic_rule_ids") or []:
        canonical_id = REVIEWED_SEMANTIC_RULE_CANONICAL_CONCEPTS.get(_clean(semantic_rule_id))
        if canonical_id:
            specific.append(("supporting_semantic_rule_ids", canonical_id))

    specific_families: set[str] = set()
    for _, token in specific:
        concept = resolve_canonical_football_concept(token)
        if concept is not None and _clean(concept.get("family")):
            specific_families.add(_clean(concept.get("family")).upper())

    values: list[tuple[str, str]] = list(specific)
    primary = _clean(candidate.get("primary_family_candidate"))
    if primary and primary.upper() not in specific_families:
        values.append(("primary_family_candidate", primary))

    cardinality = candidate.get("observation_occurrence_cardinality")
    if isinstance(cardinality, dict):
        family = _clean(cardinality.get("action_family_candidate"))
        if family and family.upper() not in specific_families:
            values.append(("observation_occurrence_cardinality.action_family_candidate", family))

    for value in candidate.get("action_family_candidates") or []:
        family = _clean(value)
        if family and family.upper() not in specific_families:
            values.append(("action_family_candidates", family))

    seen: set[str] = set()
    result: list[tuple[str, str]] = []
    for source, token in values:
        key = token.upper()
        if key in seen:
            continue
        seen.add(key)
        result.append((source, token))
    return result


def bind_canonical_football_grammar_metadata(occurrence_payload: dict[str, Any]) -> dict[str, Any]:
    """Attach canonical football-language metadata to admitted occurrence candidates.

    The binder is explanation/normalization only. It never changes occurrence
    identity, evidence support, admission class, dependency, chronology, claim
    ceiling, or finding eligibility. Unresolved admitted semantic tokens remain
    visible instead of being fuzzily coerced into the nearest canonical concept.
    """
    candidates = [
        row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    resolved_candidate_count = 0
    fully_resolved_candidate_count = 0
    unresolved_candidate_count = 0
    unresolved_tokens: Counter[str] = Counter()
    canonical_id_counts: Counter[str] = Counter()

    for candidate in candidates:
        matches: list[dict[str, Any]] = []
        unresolved: list[dict[str, str]] = []
        tokens = _canonical_family_tokens(candidate)
        for source, token in tokens:
            concept = resolve_canonical_football_concept(token)
            if concept is None:
                unresolved.append({"source": source, "token": token})
                unresolved_tokens[token] += 1
                continue
            canonical_id = _clean(concept.get("id"))
            if canonical_id:
                canonical_id_counts[canonical_id] += 1
            matches.append(
                {
                    "source": source,
                    "source_token": token,
                    "canonical_id": concept.get("id"),
                    "class": concept.get("class"),
                    "family": concept.get("family"),
                    "label_tr": concept.get("label_tr"),
                    "label_en": concept.get("label_en"),
                    "definition": concept.get("definition"),
                    "required_observations": list(concept.get("required_observations") or []),
                    "forbidden_inferences": list(concept.get("forbidden_inferences") or []),
                    "claim_ceiling": concept.get("claim_ceiling"),
                }
            )

        candidate["canonical_football_grammar_matches"] = matches
        candidate["canonical_football_grammar_unresolved_tokens"] = unresolved
        candidate["canonical_football_grammar_match_count"] = len(matches)
        candidate["canonical_football_grammar_binding_creates_new_evidence"] = False
        candidate["canonical_football_grammar_binding_changes_occurrence_identity"] = False
        candidate["canonical_football_grammar_binding_can_authorize_emit"] = False

        if matches:
            resolved_candidate_count += 1
        if tokens and matches and not unresolved:
            fully_resolved_candidate_count += 1
        if unresolved:
            unresolved_candidate_count += 1

    occurrence_payload["canonical_football_grammar_registry_id"] = (
        load_canonical_football_grammar_registry().get("registry_id")
    )
    occurrence_payload["canonical_football_grammar_candidate_count"] = len(candidates)
    occurrence_payload["canonical_football_grammar_resolved_candidate_count"] = resolved_candidate_count
    occurrence_payload["canonical_football_grammar_fully_resolved_candidate_count"] = fully_resolved_candidate_count
    occurrence_payload["canonical_football_grammar_unresolved_candidate_count"] = unresolved_candidate_count
    occurrence_payload["canonical_football_grammar_unresolved_token_counts"] = dict(
        sorted(unresolved_tokens.items())
    )
    occurrence_payload["canonical_football_grammar_id_counts"] = dict(
        sorted(canonical_id_counts.items())
    )
    occurrence_payload["canonical_football_grammar_binding_status"] = (
        "PASS" if candidates and unresolved_candidate_count == 0
        else "REVIEW_REQUIRED" if candidates
        else "NOT_EVALUATED"
    )
    occurrence_payload["canonical_football_grammar_binding_creates_new_evidence"] = False
    occurrence_payload["canonical_football_grammar_binding_changes_occurrence_identity"] = False
    occurrence_payload["canonical_football_grammar_binding_changes_admission"] = False
    occurrence_payload["canonical_football_grammar_binding_can_authorize_emit"] = False
    return occurrence_payload


def _goal_kick_matching_view(action_payload: dict[str, Any]) -> dict[str, Any]:
    """Build a local label view for exact goalkeeper goal-kick grammar matching.

    Real provider surfaces may carry a raw label such as ``goal kicks long (40+ m)``
    plus a punctuation-stripped normalized alias such as ``goal kicks long 40 m``.
    Those are two spellings of the same reviewed observation, not two independent
    semantic labels. Goal-kick exact matching therefore uses raw provider labels when
    present and falls back to normalized labels only when raw labels are absent.

    This local view never mutates upstream Action Bundle truth; reviewed Evidence Atom
    semantic-rule IDs remain mandatory authority for admission.
    """
    local = copy.deepcopy(action_payload)
    for bundle in local.get("action_bundle_candidates") or []:
        if not isinstance(bundle, dict):
            continue
        if _clean(bundle.get("source_role")) != "GOALKEEPER_SURFACE_CANDIDATE":
            continue
        raw_labels = [_clean(value) for value in bundle.get("raw_labels") or [] if _clean(value)]
        if raw_labels:
            bundle["normalized_labels"] = list(raw_labels)
    return local


def _reconcile_goal_kick_product_summary(occurrence_payload: dict[str, Any]) -> None:
    """Make R6 summary fields describe the final occurrence product state.

    The goal-kick binder can be reached more than once by the current composition path.
    A later idempotent pass may admit zero *new* rows while the already-admitted rows
    remain present in the product. Summary fields must therefore describe the final
    candidate surface rather than only the rows newly appended by the latest call.

    This reconciliation creates no evidence and changes no admission decision. It only
    derives counts from already-admitted semantic occurrence candidates.
    """
    effective = [
        row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
        and _clean(row.get("interaction_type"))
        == "GOAL_KICK_RESTART_PASS_SEMANTIC_CANDIDATE"
    ]
    occurrence_payload["goal_kick_restart_pass_candidate_count"] = len(effective)
    occurrence_payload["goal_kick_restart_pass_candidates"] = effective
    occurrence_payload["goal_kick_provider_distance_bucket_counts"] = dict(
        sorted(
            Counter(
                _clean((row.get("attributes") or {}).get("provider_distance_bucket_candidate"))
                for row in effective
                if _clean((row.get("attributes") or {}).get("provider_distance_bucket_candidate"))
            ).items()
        )
    )
    occurrence_payload["goal_kick_pass_outcome_counts"] = dict(
        sorted(
            Counter(
                _clean((row.get("attributes") or {}).get("pass_outcome_candidate"))
                for row in effective
                if _clean((row.get("attributes") or {}).get("pass_outcome_candidate"))
            ).items()
        )
    )
    occurrence_payload["goal_kick_summary_basis"] = "FINAL_ADMITTED_OCCURRENCE_PRODUCT_STATE"
    occurrence_payload["goal_kick_summary_creates_new_evidence"] = False
    occurrence_payload["goal_kick_summary_can_authorize_emit"] = False


def bind_intra_actor_action_grammar(
    occurrence_payload: dict[str, Any],
    action_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    """Extend current occurrence product with reviewed same-actor semantic candidates.

    Existing two-participant interaction candidates remain untouched. Multi-label Action Grammar
    candidates are added first. A separate, stricter single-action-anchor admission then admits only
    one-label Action Bundles backed by one exact reviewed ACTION_ANCHOR Evidence Atom and not already
    represented by an existing occurrence. The reviewed goalkeeper goal-kick RESTART+PASS grammar is
    then bound through its exact same-actor/time/anchor contract. None of these paths establishes
    canonical event truth or true physical-action count. Observation-to-occurrence cardinality remains
    an audit/admission contract rather than event truth.
    """
    if occurrence_payload.get("status") == "FAIL_CLOSED":
        return occurrence_payload

    grammar = build_intra_actor_action_grammar_candidates(
        action_payload,
        evidence_payload,
        registry,
    )
    existing = [
        row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    grammar_candidates = [
        row
        for row in grammar.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]

    single_anchor = build_single_action_anchor_candidates(
        action_payload,
        evidence_payload,
        existing + grammar_candidates,
    )
    single_anchor_candidates = [
        row
        for row in single_anchor.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    combined = existing + grammar_candidates + single_anchor_candidates

    cardinality = bind_observation_occurrence_cardinality(
        action_payload,
        evidence_payload,
        registry,
        combined,
    )

    occurrence_payload["action_occurrence_candidates"] = combined
    occurrence_payload["action_occurrence_candidate_count"] = len(combined)
    occurrence_payload["interaction_occurrence_candidate_count"] = len(existing)
    occurrence_payload["intra_actor_action_grammar_candidate_count"] = len(grammar_candidates)
    occurrence_payload["intra_actor_action_grammar_candidates"] = grammar_candidates
    occurrence_payload["single_action_anchor_occurrence_candidate_count"] = len(single_anchor_candidates)
    occurrence_payload["single_action_anchor_occurrence_candidates"] = single_anchor_candidates
    occurrence_payload["single_action_anchor_family_counts"] = single_anchor.get("admitted_family_counts") or {}
    occurrence_payload["single_action_anchor_source_role_counts"] = single_anchor.get("admitted_source_role_counts") or {}
    occurrence_payload["single_action_anchor_not_admitted_with_reason_counts"] = single_anchor.get(
        "not_admitted_with_reason_counts"
    ) or {}
    occurrence_payload["semantic_consumer_coverage_state_vocabulary"] = single_anchor.get(
        "consumer_coverage_state_vocabulary"
    ) or []
    occurrence_payload["unknown_downstream_usage_is_not_non_use"] = True
    occurrence_payload["intra_actor_action_grammar_rejected_provider_semantics_binding_count"] = int(
        grammar.get("rejected_provider_semantics_binding_count") or 0
    )
    occurrence_payload["intra_actor_action_grammar_contradictory_semantics_count"] = int(
        grammar.get("contradictory_semantics_count") or 0
    )
    occurrence_payload["same_timestamp_alone_is_merge_authority"] = False
    occurrence_payload["cross_bundle_action_grammar_merge_allowed"] = False
    occurrence_payload["single_label_alone_is_event_truth"] = False

    occurrence_payload["observation_occurrence_cardinality_records"] = cardinality.get("records") or []
    occurrence_payload["observation_occurrence_cardinality_record_count"] = int(cardinality.get("record_count") or 0)
    occurrence_payload["observation_occurrence_cardinality_state_counts"] = cardinality.get("state_counts") or {}
    occurrence_payload["observation_occurrence_cardinality_state_vocabulary"] = cardinality.get("state_vocabulary") or []
    occurrence_payload["observation_occurrence_cardinality_claim_ceiling"] = cardinality.get("claim_ceiling")
    occurrence_payload["cardinality_out_of_scope_interaction_occurrence_candidate_count"] = int(
        cardinality.get("out_of_scope_interaction_occurrence_candidate_count") or 0
    )
    occurrence_payload["row_count_is_action_count"] = False
    occurrence_payload["label_count_is_action_count"] = False
    occurrence_payload["same_actor_same_timestamp_is_single_action_authority"] = False
    occurrence_payload["shared_base_label_is_sufficient_collapse_authority"] = False
    occurrence_payload["multiple_rows_automatically_single_occurrence"] = False
    occurrence_payload["cardinality_resolution_is_physical_action_truth"] = False

    class_counts: dict[str, int] = {}
    interaction_counts: dict[str, int] = {}
    for candidate in combined:
        admission_class = _clean(candidate.get("admission_class"))
        interaction = _clean(candidate.get("interaction_type"))
        if admission_class:
            class_counts[admission_class] = class_counts.get(admission_class, 0) + 1
        if interaction:
            interaction_counts[interaction] = interaction_counts.get(interaction, 0) + 1
    occurrence_payload["admission_class_counts"] = dict(sorted(class_counts.items()))
    occurrence_payload["interaction_type_counts"] = dict(sorted(interaction_counts.items()))

    existing_rejected_provider = int(
        occurrence_payload.get("candidate_rejected_provider_semantics_binding_count") or 0
    )
    grammar_rejected_provider = int(
        grammar.get("rejected_provider_semantics_binding_count") or 0
    )
    total_rejected_provider = existing_rejected_provider + grammar_rejected_provider
    occurrence_payload["candidate_rejected_provider_semantics_binding_count"] = total_rejected_provider

    hard_blocks = list(occurrence_payload.get("hard_block_hits") or [])
    hard_blocks.extend(cardinality.get("hard_block_hits") or [])
    occurrence_payload["hard_block_hits"] = sorted({_clean(value) for value in hard_blocks if _clean(value)})

    reviews = list(occurrence_payload.get("review_hits") or [])
    reviews.extend(grammar.get("review_hits") or [])
    reviews.extend(cardinality.get("review_hits") or [])
    if total_rejected_provider:
        reviews.append("candidate_rejected_provider_semantics_binding")
        occurrence_payload["provider_semantics_binding_status"] = "REVIEW_REQUIRED"
    elif combined:
        occurrence_payload["provider_semantics_binding_status"] = "PASS"
    elif occurrence_payload.get("provider_semantics_binding_status") == "FAIL_CLOSED":
        pass
    else:
        occurrence_payload["provider_semantics_binding_status"] = "PASS"

    occurrence_payload["review_hits"] = sorted({_clean(value) for value in reviews if _clean(value)})
    if occurrence_payload["hard_block_hits"]:
        occurrence_payload["status"] = "FAIL_CLOSED"
        occurrence_payload["module_status"] = "FAIL_CLOSED"
    elif (grammar.get("review_hits") or cardinality.get("review_hits")) and occurrence_payload.get("status") != "FAIL_CLOSED":
        occurrence_payload["status"] = "REVIEW_REQUIRED"
        occurrence_payload["module_status"] = "REVIEW_REQUIRED"

    # R6: bind only the explicitly reviewed goalkeeper goal-kick RESTART+PASS
    # cross-bundle semantic grammar. Real provider bundles can carry a raw label and
    # its normalized spelling simultaneously; the local view prevents that alias from
    # masquerading as a second semantic label while preserving reviewed rule-ID checks.
    occurrence_payload = bind_goal_kick_restart_pass_grammar(
        occurrence_payload,
        _goal_kick_matching_view(action_payload),
        evidence_payload,
    )
    _reconcile_goal_kick_product_summary(occurrence_payload)
    occurrence_payload["goal_kick_raw_label_preferred_for_exact_matching"] = True
    occurrence_payload["goal_kick_normalized_label_is_independent_semantic_support"] = False

    # Final semantic explanation layer: attach provider-independent canonical
    # football concepts only after occurrence admission has finished. This does
    # not participate in identity, dependency, support, chronology or admission.
    occurrence_payload = bind_canonical_football_grammar_metadata(occurrence_payload)

    occurrence_payload["canonical_event_count"] = "UNKNOWN"
    occurrence_payload["true_action_count"] = "UNKNOWN"
    occurrence_payload["production_release"] = False
    return occurrence_payload
