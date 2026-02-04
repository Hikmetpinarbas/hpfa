from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


@dataclass
class RegistryIssue:
    metric_key: str
    file: str
    issue: str


class RegistryGate:
    """
    Contract-first registry loader + validator.

    Goals:
      - No silent acceptance of half-baked metric specs.
      - Use filename stem as the canonical metric_key (e.g. ppda.yaml -> "ppda")
        so code can map to MetricEngine.compute_ppda.
      - Attach meta fields for traceability (_file, _key).
    """

    # Minimum constitutional blocks (you can tighten this later)
    REQUIRED_TOP_LEVEL_BLOCKS = [
        "metric_name",          # human label
        "category",             # tactical/technical/physical/psychological
        "formula",              # at least as a string/pseudocode for now
        "unit",                 # unit discipline
        "aggregation",          # entity_level + rollup
        "temporal",             # time_grain / windows (explicit even if "match")
        "benchmarks",           # context-aware thresholds OR explicitly empty + reason
        "falsifiability",       # H0/supports/contradicts OR explicitly blocked
        "relationships",        # influences/influenced_by OR explicit "relationless_reason"
    ]

    def load_registry_dir(self, registry_dir: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        """
        Returns:
          registry: {metric_key: metric_meta}
          report: {status, issues[], loaded_count}
        """
        if not registry_dir.exists():
            raise FileNotFoundError(f"Registry directory not found: {registry_dir}")

        yamls = sorted(registry_dir.glob("*.yaml"))
        if not yamls:
            raise ValueError(f"No YAML files found in registry directory: {registry_dir}")

        registry: Dict[str, Dict[str, Any]] = {}
        issues: List[RegistryIssue] = []

        for p in yamls:
            metric_key = p.stem.strip().lower().replace("-", "_").replace(" ", "_")
            with p.open("r", encoding="utf-8") as f:
                d = yaml.safe_load(f) or {}

            # Attach trace
            d["_file"] = str(p)
            d["_key"] = metric_key

            # Validate required blocks
            missing = [k for k in self.REQUIRED_TOP_LEVEL_BLOCKS if k not in d]
            if missing:
                issues.append(
                    RegistryIssue(
                        metric_key=metric_key,
                        file=str(p),
                        issue=f"MISSING_BLOCKS: {missing}",
                    )
                )

            # Minimal structural checks (non-exhaustive, but catches common breakages)
            if "aggregation" in d and isinstance(d["aggregation"], dict):
                if "entity_level" not in d["aggregation"]:
                    issues.append(RegistryIssue(metric_key, str(p), "aggregation.entity_level missing"))
            if "temporal" in d and isinstance(d["temporal"], dict):
                if "time_grain" not in d["temporal"]:
                    issues.append(RegistryIssue(metric_key, str(p), "temporal.time_grain missing"))

            registry[metric_key] = d

        status = "HEALTHY" if len(issues) == 0 else "DEGRADED"

        report = {
            "status": status,
            "loaded_count": len(registry),
            "issues": [
                {"metric_key": i.metric_key, "file": i.file, "issue": i.issue}
                for i in issues
            ],
        }
        return registry, report