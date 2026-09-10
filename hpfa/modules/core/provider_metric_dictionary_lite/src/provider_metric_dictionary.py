from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from . import _provider_metric_dictionary_impl_v7 as _impl
from ._provider_metric_dictionary_impl_v7 import *  # noqa: F401,F403


ZFGV_CAPABILITY_BY_SURFACE_ROLE = {
    "occurrence_candidate": "ACTION_EVENT",
    "aggregate_candidate": "AGGREGATE_TABULAR",
    "entity_candidate": "ENTITY_ACTOR",
    "temporal_candidate": "TEMPORAL",
    "spatial_candidate": "SPATIAL",
    "process_candidate": "PROCESS_PARTICIPATION",
    "relational_candidate": "RELATIONAL",
    "outcome_candidate": "OUTCOME_QUALIFIER",
}


def _missing_required_derivation_denominator_policy_blocks(
    dictionary: dict[str, Any],
    derivations: dict[str, Any],
    metric_policy: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Fail closed when a CLEARED derivation omits its target's admitted denominator policy."""
    metrics = dictionary.get("metrics", [])
    definition_index = {
        "::".join((
            str(row.get("provider_id") or "").strip(),
            str(row.get("provider_version") or "").strip(),
            str(row.get("metric_id") or "").strip(),
        )): row
        for row in metrics
        if str(row.get("metric_id") or "").strip()
    }
    policy_index, duplicate_policy_ids = _impl._unique_index(
        (metric_policy or {}).get("metrics", []), "metric_id"
    )

    blocks: list[dict[str, str]] = []
    for row in derivations.get("derivations", []):
        if row.get("derivation_status") != "CLEARED":
            continue
        provider_id = str(row.get("provider_id") or "").strip()
        provider_version = str(row.get("provider_version") or "").strip()
        metric_id = str(row.get("metric_id") or "").strip()
        if not provider_id or not provider_version or not metric_id:
            continue

        target_key = f"{provider_id}::{provider_version}::{metric_id}"
        target = definition_index.get(target_key)
        if target is None:
            continue
        upstream = target.get("upstream_bindings") or {}
        if not isinstance(upstream, dict):
            continue
        target_policy_id = str(upstream.get("metric_policy_id") or "").strip()
        if not target_policy_id or target_policy_id in duplicate_policy_ids:
            continue
        target_policy = policy_index.get(target_policy_id)
        if target_policy is None:
            continue

        expected_denominator_policy_id = str(
            target_policy.get("denominator_policy_id") or ""
        ).strip()
        if not expected_denominator_policy_id:
            continue
        declared_denominator_policy_id = str(
            row.get("upstream_denominator_policy_id") or ""
        ).strip()
        if not declared_denominator_policy_id:
            blocks.append(_impl._gap(
                "cleared_derivation_required_denominator_policy_missing",
                f"{target_key}:expected={expected_denominator_policy_id}",
            ))
    return blocks


def _explicit_capabilities(row: dict[str, Any]) -> list[str]:
    raw = row.get("required_observation_capabilities")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    return sorted({str(item).strip().upper() for item in raw if str(item).strip()})


def _legacy_event_only_metadata_blocks(
    dictionary: dict[str, Any],
    metric_policy: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Keep legacy compatibility metadata well-formed and require a real ZFGV replacement.

    event_only_compatible=False is not itself forbidden anymore.  But a record may
    leave the historical event-only regime only when it declares the observation
    capabilities that replace that legacy gate.  This prevents a blind relaxation
    from turning into an implicit unlimited claim ceiling.
    """
    blocks: list[dict[str, str]] = []
    for family, rows in (
        ("provider_dictionary", dictionary.get("metrics", [])),
        ("metric_policy", (metric_policy or {}).get("metrics", [])),
    ):
        for row in rows:
            metric_id = str(row.get("metric_id") or "UNKNOWN").strip() or "UNKNOWN"
            if "event_only_compatible" not in row:
                continue
            compatibility = row.get("event_only_compatible")
            if not isinstance(compatibility, bool):
                blocks.append(_impl._gap(
                    "event_only_compatibility_metadata_invalid",
                    f"{family}:{metric_id}",
                ))
                continue
            if compatibility is False and not _explicit_capabilities(row):
                blocks.append(_impl._gap(
                    "event_only_compatibility_required",
                    f"{family}:{metric_id}:legacy_gate_replacement_missing_required_observation_capabilities",
                ))
    return blocks


def _neutralize_legacy_event_only_gate(
    dictionary: dict[str, Any],
    metric_policy: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Adapt only explicitly migrated records for the historical v7 validator.

    Records that remain event-only compatible are passed through untouched so all
    existing operational fingerprints, namespace checks and derivation contracts
    retain their original evidentiary meaning.  A record marked false is normalized
    only when an explicit ZFGV capability contract replaces the old gate.
    """
    dictionary_view = copy.deepcopy(dictionary)
    policy_view = copy.deepcopy(metric_policy) if metric_policy is not None else None

    for row in dictionary_view.get("metrics", []):
        if row.get("event_only_compatible") is False and _explicit_capabilities(row):
            row["event_only_compatible"] = True
            if "operational_semantic_fingerprint_sha256" in row:
                row["operational_semantic_fingerprint_sha256"] = ""

    for row in (policy_view or {}).get("metrics", []):
        if row.get("event_only_compatible") is False and _explicit_capabilities(row):
            row["event_only_compatible"] = True

    return dictionary_view, policy_view


def _required_observation_capabilities(
    dictionary_row: dict[str, Any],
    policy_row: dict[str, Any] | None,
) -> list[str]:
    """Describe all known construct prerequisites; never let one source erase another."""
    policy = policy_row or {}
    required: set[str] = set(_explicit_capabilities(dictionary_row))
    required.update(_explicit_capabilities(policy))

    for role in policy.get("source_surface_roles") or []:
        capability = ZFGV_CAPABILITY_BY_SURFACE_ROLE.get(str(role).strip().lower())
        if capability:
            required.add(capability)

    if policy.get("required_event_families"):
        required.add("ACTION_EVENT")
    if policy.get("entity_scope") or dictionary_row.get("eligibility_scope"):
        required.add("ENTITY_ACTOR")
    if policy.get("observation_window") or dictionary_row.get("temporal_window"):
        required.add("TEMPORAL")

    spatial_rule = str(dictionary_row.get("spatial_rule") or "").strip().upper()
    if spatial_rule and spatial_rule not in {"NOT_APPLICABLE", "NONE", "UNKNOWN"}:
        required.add("SPATIAL")

    aggregation_level = str(dictionary_row.get("aggregation_level") or "").strip().lower()
    if "aggregate" in aggregation_level or "tabular" in aggregation_level:
        required.add("AGGREGATE_TABULAR")

    return sorted(required)


def _zfgv_capability_projection(
    dictionary: dict[str, Any],
    metric_policy: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    policy_index = {
        str(row.get("metric_id") or "").strip(): row
        for row in (metric_policy or {}).get("metrics", [])
        if str(row.get("metric_id") or "").strip()
    }
    projection: list[dict[str, Any]] = []
    for row in dictionary.get("metrics", []):
        metric_id = str(row.get("metric_id") or "").strip()
        upstream = row.get("upstream_bindings") or {}
        policy_id = str(upstream.get("metric_policy_id") or "").strip() if isinstance(upstream, dict) else ""
        policy_row = policy_index.get(policy_id)
        dictionary_explicit = _explicit_capabilities(row)
        policy_explicit = _explicit_capabilities(policy_row or {})
        required = _required_observation_capabilities(row, policy_row)
        projection.append({
            "metric_id": metric_id,
            "event_only_compatible_legacy_metadata": row.get("event_only_compatible"),
            "event_only_compatibility_is_global_admission_gate": False,
            "required_observation_capabilities": required,
            "capability_contract_explicit": bool(dictionary_explicit or policy_explicit),
            "dictionary_capability_contract_explicit": bool(dictionary_explicit),
            "policy_capability_contract_explicit": bool(policy_explicit),
            "capability_requirement_sources_are_union_preserved": True,
            "runtime_capability_admission_evaluated": False,
            "metric_value_output_allowed_by_this_projection": False,
            "construct_truth_granted_by_this_projection": False,
        })
    return projection


def build_dictionary_report(
    dictionary: dict[str, Any],
    aliases: dict[str, Any],
    derivations: dict[str, Any],
    conflicts: dict[str, Any],
    *,
    metric_policy: dict[str, Any] | None = None,
    denominator_policy: dict[str, Any] | None = None,
    aggregate_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_blocks = _legacy_event_only_metadata_blocks(dictionary, metric_policy)
    dictionary_view, policy_view = _neutralize_legacy_event_only_gate(
        dictionary, metric_policy
    )

    report = _impl.build_dictionary_report(
        dictionary_view,
        aliases,
        derivations,
        conflicts,
        metric_policy=policy_view,
        denominator_policy=denominator_policy,
        aggregate_registry=aggregate_registry,
    )

    extra_blocks = [
        *metadata_blocks,
        *_missing_required_derivation_denominator_policy_blocks(
            dictionary, derivations, metric_policy
        ),
    ]
    if extra_blocks:
        existing = {
            (str(gap.get("gap_type")), str(gap.get("detail")))
            for gap in report.get("hard_block_hits", [])
        }
        report.setdefault("hard_block_hits", []).extend(
            gap
            for gap in extra_blocks
            if (str(gap.get("gap_type")), str(gap.get("detail"))) not in existing
        )
        report["status"] = "FAIL_CLOSED"
        report["spec_contract_valid"] = False
        report["downstream_provider_definition_gate_open"] = False

    report["zfgv_observation_model"] = "MULTI_SURFACE_FOOTBALL_OBSERVATION_FABRIC"
    report["event_only_compatibility_is_global_admission_gate"] = False
    report["event_only_compatibility_is_legacy_metadata"] = True
    report["metric_admission_policy"] = "REQUIRED_CAPABILITIES_SUBSET_OF_ADMITTED_CAPABILITIES"
    report["runtime_capability_admission_evaluated"] = False
    report["zfgv_metric_capability_requirements"] = _zfgv_capability_projection(
        dictionary, metric_policy
    )
    report["metric_capability_requirement_sources_are_union_preserved"] = True
    report["metric_value_output_allowed_by_zfgv_projection"] = False
    report["construct_truth_granted_by_zfgv_projection"] = False
    return report


def load_dictionary_pack(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root)
    config_dir = root / "configs" / "metrics"
    aggregate_path = (
        root
        / "hpfa"
        / "modules"
        / "core"
        / "aggregate_definition_alignment_lite"
        / "registry"
        / "sportsbase_aggregate_definition_candidates_v1.json"
    )
    return build_dictionary_report(
        _impl._load(config_dir / "provider_metric_dictionary_v1.json"),
        _impl._load(config_dir / "provider_alias_registry_v1.json"),
        _impl._load(config_dir / "metric_derivation_registry_v1.json"),
        _impl._load(config_dir / "metric_conflict_queue_v1.json"),
        metric_policy=_impl._load(config_dir / "metric_registry_v1.json"),
        denominator_policy=_impl._load(config_dir / "metric_denominator_policy_v1.json"),
        aggregate_registry=_impl._load(aggregate_path),
    )


def write_dictionary_report(repo_root: str | Path, output: str | Path) -> dict[str, Any]:
    report = load_dictionary_pack(repo_root)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
