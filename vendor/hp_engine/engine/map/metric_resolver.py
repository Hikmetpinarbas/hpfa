from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("–", "-").replace("—", "-")
    return s


@dataclass(frozen=True)
class ResolveResult:
    canonical_family: Optional[str]
    match: str
    details: dict


class MetricResolver:
    """
    Canonical resolver using:
      - canon/ontology/<existing metric ontology json> (aliases + canonical family ids)
      - canon/mappings/platform_mappings.json (canonical_to_platforms)

    platform_mappings.json is CANONICAL_LABEL -> {Platform: RawMetricName}
    We invert it to (platform, raw_metric) -> canonical_family
    """

    def __init__(
        self,
        ontology_path: str = "canon/ontology/metric_ontology.json",
        mappings_path: str = "canon/mappings/platform_mappings.json",
    ) -> None:
        self.ontology_path = Path(ontology_path)
        self.mappings_path = Path(mappings_path)

        self.ontology = self._load_json(self.ontology_path)
        self.mappings = self._load_json(self.mappings_path)

        # alias -> canonical_family_id (from ontology)
        self.alias_to_canonical: dict[str, str] = {}
        fams = (self.ontology or {}).get("canonical_families", {})
        if isinstance(fams, dict):
            for canonical_id, meta in fams.items():
                self.alias_to_canonical[_norm(canonical_id)] = canonical_id
                if isinstance(meta, dict):
                    nm = meta.get("name")
                    if isinstance(nm, str) and nm.strip():
                        self.alias_to_canonical[_norm(nm)] = canonical_id
                    tr = meta.get("turkish")
                    if isinstance(tr, str) and tr.strip():
                        self.alias_to_canonical[_norm(tr)] = canonical_id
                    for a in (meta.get("aliases", []) or []):
                        if isinstance(a, str) and a.strip():
                            self.alias_to_canonical[_norm(a)] = canonical_id

        # (platform, raw_metric) -> canonical_family_id
        self.platform_raw_to_canonical: dict[tuple[str, str], str] = {}

        c2p = (self.mappings or {}).get("canonical_to_platforms", {})
        if isinstance(c2p, dict):
            for canonical_label, plat_map in c2p.items():
                if not isinstance(plat_map, dict):
                    continue

                # canonical_label might be "xG", "PSxG", "PPDA", "Possession Value", etc.
                canonical_id = self.alias_to_canonical.get(_norm(canonical_label))
                if canonical_id is None:
                    # unknown label; skip (better than wrong mapping)
                    continue

                for platform, raw_name in plat_map.items():
                    if not (isinstance(platform, str) and isinstance(raw_name, str)):
                        continue
                    self.platform_raw_to_canonical[(_norm(platform), _norm(raw_name))] = canonical_id

                # optional "All": apply mapping for any platform token
                if "All" in plat_map and isinstance(plat_map["All"], str):
                    self.platform_raw_to_canonical[("all", _norm(plat_map["All"]))] = canonical_id

    @staticmethod
    def _load_json(p: Path) -> Any:
        if not p.exists():
            raise FileNotFoundError(f"Missing file: {p.as_posix()}")
        return json.loads(p.read_text(encoding="utf-8"))

    def resolve(self, raw_metric_name: str, platform: Optional[str] = None) -> ResolveResult:
        raw_n = _norm(raw_metric_name)
        plat_n = _norm(platform) if platform else None
        details = {"raw": raw_metric_name, "raw_norm": raw_n, "platform": platform}

        # 1) platform mapping (strongest)
        if plat_n:
            hit = self.platform_raw_to_canonical.get((plat_n, raw_n))
            if hit:
                return ResolveResult(hit, "platform_mapping_inverted", details)

            # allow generic mapping via "All"
            hit = self.platform_raw_to_canonical.get(("all", raw_n))
            if hit:
                return ResolveResult(hit, "platform_mapping_all", details)

        # 2) ontology alias/name
        hit = self.alias_to_canonical.get(raw_n)
        if hit:
            return ResolveResult(hit, "ontology_alias", details)

        return ResolveResult(None, "unknown", details)