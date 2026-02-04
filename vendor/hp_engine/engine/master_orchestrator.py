from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .metric_engine import MetricEngine
from .popper_gate import PopperGate
from .plotspec_factory import PlotSpecFactory
from .registry_gate import RegistryGate
from .sot_validator import SOTValidator
from .provider.sportsbase import to_canonical_events


def _canonical_df_to_events(canonical_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Convert canonical event DataFrame to MetricEngine event list format.

    MetricEngine expects:
      {team: 'team'|'opponent', type: <event_type>, x: float, y: float, timestamp_s: float}
    """
    if canonical_df.empty:
        return []

    team_id_mode = canonical_df["team_id"].mode().iloc[0] if "team_id" in canonical_df.columns else None

    def role(tid):
        if team_id_mode is None:
            return "team"
        return "team" if tid == team_id_mode else "opponent"

    events: List[Dict[str, Any]] = []
    for row in canonical_df.itertuples(index=False):
        d = row._asdict() if hasattr(row, "_asdict") else dict(zip(canonical_df.columns, row))
        events.append(
            {
                "team": role(d.get("team_id")),
                "type": d.get("event_type"),
                "x": float(d.get("x")) if d.get("x") is not None else None,
                "y": float(d.get("y")) if d.get("y") is not None else None,
                "timestamp_s": float(d.get("timestamp_s")) if d.get("timestamp_s") is not None else None,
            }
        )
    return events


@dataclass
class EngineResult:
    validation_report: Dict[str, Any]
    registry_report: Dict[str, Any]
    registry_used: Dict[str, Any]
    features: Dict[str, Any]
    claims: List[Dict[str, Any]]
    plotspecs: List[Dict[str, Any]]
    narrative: str
    canonical_events_preview: pd.DataFrame


class MasterOrchestrator:
    """
    HP-Engine v3 pipeline (minimum working backbone).

    Run order (hard rule):
      Raw -> ProviderMap -> SOT -> RegistryGate -> MetricCompute -> PopperGate -> PlotSpec -> Narrative

    Principles:
      - No silent data loss.
      - Any missing capability is explicitly flagged (BLOCKED / NEEDS_EVIDENCE / CONFLICT).
      - Registry must be contract-checked before computation.
    """

    def __init__(
        self,
        registry_root: str | Path = "canon/registry",
        provider: str = "sportsbase",
    ) -> None:
        self.registry_root = Path(registry_root)
        self.provider = provider

        self.sot_gate = SOTValidator(provider_contract=provider)
        self.registry_gate = RegistryGate()
        self.metric_engine = MetricEngine()
        self.popper_gate = PopperGate()
        self.plotspec_factory = PlotSpecFactory()

    def run(
        self,
        input_df: pd.DataFrame,
        phase: str = "tactical",
        context: Optional[Dict[str, Any]] = None,
    ) -> EngineResult:
        context = context or {}

        # 1) Provider mapping -> canonical schema
        mapped = to_canonical_events(input_df)
        canonical_df = mapped.canonical_df

        # 2) SOT gate (no silent drops)
        val_report, canonical_df = self.sot_gate.validate(canonical_df)
        val_report["provider_mapping_used"] = mapped.mapping_used

        # 3) RegistryGate (contract-first)
        registry_dir = self.registry_root / phase
        registry, registry_report = self.registry_gate.load_registry_dir(registry_dir)

        # 4) Compute metrics implemented in MetricEngine
        events = _canonical_df_to_events(canonical_df)

        features: Dict[str, Any] = {}
        for metric_key, meta in registry.items():
            compute_fn = getattr(self.metric_engine, f"compute_{metric_key}", None)

            if callable(compute_fn):
                try:
                    features[metric_key] = compute_fn(events, team="team")
                except Exception as e:
                    features[metric_key] = {
                        "status": "ERROR",
                        "error": str(e),
                        "metric_name": meta.get("metric_name", metric_key.upper()),
                        "_key": metric_key,
                        "_file": meta.get("_file"),
                    }
            else:
                features[metric_key] = {
                    "status": "BLOCKED",
                    "reason": "NOT_IMPLEMENTED",
                    "metric_name": meta.get("metric_name", metric_key.upper()),
                    "expected_function": f"compute_{metric_key}",
                    "_key": metric_key,
                    "_file": meta.get("_file"),
                }

        # 5) Popper gate (falsifiability & contradictions)
        claims = self.popper_gate.verify(features=features, registry=registry)

        # 6) Plot specs (no heavy drawing here)
        plotspecs = self.plotspec_factory.generate(claims=claims)

        # 7) Narrative (v1: explicit statuses)
        narrative = self._narrative_v1(claims=claims, registry_report=registry_report, val_report=val_report)

        preview = canonical_df.head(25).copy()

        return EngineResult(
            validation_report=val_report,
            registry_report=registry_report,
            registry_used={"phase": phase, "dir": str(registry_dir), "metrics": list(registry.keys())},
            features=features,
            claims=claims,
            plotspecs=plotspecs,
            narrative=narrative,
            canonical_events_preview=preview,
        )

    @staticmethod
    def _narrative_v1(
        claims: List[Dict[str, Any]],
        registry_report: Dict[str, Any],
        val_report: Dict[str, Any],
    ) -> str:
        verified = [c for c in claims if c.get("status") == "VERIFIED"]
        other = [c for c in claims if c.get("status") != "VERIFIED"]

        lines: List[str] = []
        lines.append(f"SOT: {val_report.get('status', 'UNKNOWN')} | REGISTRY: {registry_report.get('status', 'UNKNOWN')}")
        if registry_report.get("status") != "HEALTHY":
            lines.append(f"REGISTRY_ISSUES: {len(registry_report.get('issues', []))}")

        lines.append(f"VERIFIED: {len(verified)} | OTHER: {len(other)}")

        for c in verified[:6]:
            lines.append(f"- {c.get('metric_name', c.get('metric'))}: {c.get('value')}")

        for c in other[:10]:
            lines.append(f"- {c.get('metric_name', c.get('metric'))}: {c.get('status')} ({c.get('reason','')})")

        return "\n".join(lines)