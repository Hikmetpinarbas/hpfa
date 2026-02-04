from __future__ import annotations
import json
import re
from pathlib import Path

def _norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("’", "'")
    return s

def load_6faz_map(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

def build_6faz_index(mapj: dict) -> dict:
    """
    Returns index:
      metric_norm -> {phase_id, role, raw_metric_string}
    """
    idx = {}

    # pairings: anchor / enabler / validator
    for p in mapj.get("pairings", []):
        phase_id = p.get("phase_id")
        anchor = p.get("anchor_metric", "")
        enablers = p.get("functional_enablers", "")
        validators = p.get("success_validators", "")

        def _add(raw: str, role: str):
            for part in re.split(r"[;/]", str(raw)):
                part = part.strip()
                if not part:
                    continue
                k = _norm(part)
                idx[k] = {"phase_id": phase_id, "metric_role": role, "raw": part}

        _add(anchor, "anchor")
        _add(enablers, "enabler")
        _add(validators, "validator")

    # derived metrics (explicit ids)
    for d in mapj.get("derived_metrics", []):
        phase_id = d.get("phase_id")
        name_tr = d.get("name_tr", "")
        formula = d.get("formula", "")
        metric_id = d.get("metric_id", "")

        for raw in [name_tr, formula, metric_id]:
            raw = str(raw).strip()
            if not raw:
                continue
            k = _norm(raw)
            idx.setdefault(k, {"phase_id": phase_id, "metric_role": "derived", "raw": raw})

    return idx

def tag_metric(metric_name: str, idx: dict) -> dict:
    """
    Fuzzy tagging:
    - exact normalize match
    - contains match (single-hit)
    """
    n = _norm(metric_name)
    if n in idx:
        return idx[n]

    hits = []
    for k, v in idx.items():
        if k and (k in n or n in k):
            hits.append(v)

    if len(hits) == 1:
        return hits[0]

    return {"phase_id": None, "metric_role": None, "raw": None}

