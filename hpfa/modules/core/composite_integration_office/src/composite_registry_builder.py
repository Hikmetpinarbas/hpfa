from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from source_intake_normalizer import SourceIntake, discovery_fingerprint, normalize_intake

CLAIM_SAFETY = "NO_TRUTH_UNTIL_ACTIVE_MATCH_VALIDATION"
STATUS = "CANDIDATE_REQUIRES_BOUNDARY_ANALYSIS"
ENGINE_MAP = {
    "sequence_engine": "Sequence Intelligence Engine",
    "pattern_discovery": "Pattern Discovery Engine",
    "metric_fusion": "Metric Fusion Engine",
    "productization_governance": "Governance / Release Engine",
    "data_quality_gate": "Data Quality Gate",
    "canonical_ingest": "Canonical Ingest Engine",
}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    records: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def target_engine_for(capability: str) -> str:
    return ENGINE_MAP.get(capability, "Composite Integration Office")


def build_composite_registry(raw_records: list[dict[str, Any]]) -> dict[str, Any]:
    intakes = [normalize_intake(r) for r in raw_records]
    buckets: dict[str, list[SourceIntake]] = defaultdict(list)

    for intake in intakes:
        buckets[discovery_fingerprint(intake)].append(intake)

    composites: list[dict[str, Any]] = []
    for fingerprint, members in sorted(buckets.items()):
        capability_counts = Counter(m.hpfa_capability for m in members)
        dominant_capability = capability_counts.most_common(1)[0][0]
        source_systems = sorted({m.source_system for m in members})
        stable_id = fingerprint.replace("HASH:", "COMP-")

        composites.append({
            "composite_id": stable_id,
            "fingerprint": fingerprint,
            "source_count": len(members),
            "sources": source_systems,
            "dominant_capability": dominant_capability,
            "target_hpfa_engine": target_engine_for(dominant_capability),
            "status": STATUS,
            "claim_safety": CLAIM_SAFETY,
            "active_match_validation_required": True,
            "members": [m.to_dict() for m in members],
        })

    return {
        "registry_id": "composite_registry_v1",
        "status": "PASS",
        "composite_count": len(composites),
        "claim_safety": CLAIM_SAFETY,
        "active_match_validation_required": True,
        "runtime_truth_authority": "ACTIVE_MATCH_EXECUTION_ONLY",
        "composites": composites,
    }


def write_composite_registry(raw_records: list[dict[str, Any]], out_path: str | Path) -> dict[str, Any]:
    registry = build_composite_registry(raw_records)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return registry
