from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import _provider_metric_dictionary_impl_v7 as _impl
from ._provider_metric_dictionary_impl_v7 import *  # noqa: F401,F403
from .observation_layer_admission import (
    OBSERVATION_MODEL,
    normalize_dictionary_for_zfgv,
)


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


def _merge_observation_assessments(
    report: dict[str, Any], assessments: list[dict[str, Any]]
) -> None:
    report["observation_model"] = OBSERVATION_MODEL
    report["observation_contract_assessments"] = assessments

    observation_hard = [
        _impl._gap("observation_contract_invalid", hit)
        for assessment in assessments
        for hit in assessment.get("hard_block_hits", [])
    ]
    observation_review = [
        _impl._gap("observation_contract_review", hit, "REVIEW_REQUIRED")
        for assessment in assessments
        for hit in assessment.get("review_hits", [])
    ]

    if observation_hard:
        existing = {
            (str(gap.get("gap_type")), str(gap.get("detail")))
            for gap in report.get("hard_block_hits", [])
        }
        report.setdefault("hard_block_hits", []).extend(
            gap
            for gap in observation_hard
            if (str(gap.get("gap_type")), str(gap.get("detail"))) not in existing
        )
        report["status"] = "FAIL_CLOSED"
        report["spec_contract_valid"] = False
        report["downstream_provider_definition_gate_open"] = False

    if observation_review:
        existing_review = {
            (str(gap.get("gap_type")), str(gap.get("detail")))
            for gap in report.get("review_hits", [])
        }
        report.setdefault("review_hits", []).extend(
            gap
            for gap in observation_review
            if (str(gap.get("gap_type")), str(gap.get("detail"))) not in existing_review
        )
        if report.get("status") == "PASS":
            report["status"] = "REVIEW_REQUIRED"


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
    normalized_dictionary, normalized_metric_policy, observation_assessments = (
        normalize_dictionary_for_zfgv(dictionary, metric_policy)
    )

    report = _impl.build_dictionary_report(
        normalized_dictionary,
        aliases,
        derivations,
        conflicts,
        metric_policy=normalized_metric_policy,
        denominator_policy=denominator_policy,
        aggregate_registry=aggregate_registry,
    )
    _merge_observation_assessments(report, observation_assessments)

    extra_blocks = _missing_required_derivation_denominator_policy_blocks(
        normalized_dictionary, derivations, normalized_metric_policy
    )
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
