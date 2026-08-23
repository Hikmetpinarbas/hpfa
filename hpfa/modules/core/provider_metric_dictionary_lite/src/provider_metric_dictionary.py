from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import _provider_metric_dictionary_impl_v7 as _impl
from ._provider_metric_dictionary_impl_v7 import *  # noqa: F401,F403


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
    report = _impl.build_dictionary_report(
        dictionary,
        aliases,
        derivations,
        conflicts,
        metric_policy=metric_policy,
        denominator_policy=denominator_policy,
        aggregate_registry=aggregate_registry,
    )
    extra_blocks = _missing_required_derivation_denominator_policy_blocks(
        dictionary, derivations, metric_policy
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
