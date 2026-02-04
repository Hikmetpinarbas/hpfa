from __future__ import annotations

import argparse
import glob
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml


# -------------------------
# Minimal canonical helpers
# -------------------------

def read_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_json(obj: Any, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _get(d: Dict[str, Any], path: str, default=None):
    cur: Any = d
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


# -------------------------
# Extraction from existing canon YAML (your current format)
# -------------------------

def extract_metric_id(doc: Dict[str, Any]) -> Optional[str]:
    # Prefer metadata.metric_id; fallback metric_id if exists
    mid = _get(doc, "metadata.metric_id")
    if isinstance(mid, str) and mid.strip():
        return mid.strip()
    mid2 = doc.get("metric_id")
    if isinstance(mid2, str) and mid2.strip():
        return mid2.strip()
    return None


def extract_requires_signals(doc: Dict[str, Any]) -> List[str]:
    """
    NO guessing:
    - Uses derivation.requires.raw_data + optional (if present)
    - Does not infer from formula text.
    """
    raw = _get(doc, "derivation.requires.raw_data", [])
    opt = _get(doc, "derivation.requires.optional", [])
    sigs = [str(x) for x in _as_list(raw)] + [str(x) for x in _as_list(opt)]
    # Keep stable order, unique
    seen: Set[str] = set()
    out: List[str] = []
    for s in sigs:
        s = s.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def extract_requires_metrics(doc: Dict[str, Any]) -> List[str]:
    """
    NO guessing:
    - If relationships.requires exists in canon YAML, read it.
    - Else empty.
    """
    req = _get(doc, "relationships.requires", [])
    out: List[str] = []
    for r in _as_list(req):
        if isinstance(r, dict) and "metric" in r:
            out.append(str(r["metric"]))
        elif isinstance(r, str):
            out.append(r)
    # Unique stable
    seen: Set[str] = set()
    dedup: List[str] = []
    for m in out:
        m = m.strip()
        if not m or m in seen:
            continue
        seen.add(m)
        dedup.append(m)
    return dedup


def extract_scopes(doc: Dict[str, Any]) -> List[str]:
    """
    Your YAML has analysis_modules booleans. We map true fields to scope ids.
    NO guessing beyond direct mapping.
    """
    am = doc.get("analysis_modules") or {}
    mapping = {
        "pre_match_analysis": "pre_match",
        "post_match_analysis": "post_match",
        "individual_analysis": "individual",
        "team_tactical_analysis": "team_tactical",
        "seasonal_tournament_analysis": "seasonal_tournament",
        "team_squad_engineering_analysis": "squad_engineering",
        "general_analysis": "general",
    }
    scopes: List[str] = []
    if isinstance(am, dict):
        for k, scope in mapping.items():
            if am.get(k) is True:
                scopes.append(scope)
    return scopes


def extract_citations(doc: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    NO guessing:
    - Uses academic_references list if present.
    - We split into supporting_definition only; validation_method stays empty unless explicit.
    """
    refs = _as_list(doc.get("academic_references"))
    supporting = [str(r) for r in refs if isinstance(r, (str, int, float))]
    validation = []
    # If canon yaml has validation.reproducibility notes or explicit refs, you can extend later.
    return {
        "supporting_definition": supporting,
        "validation_method": validation,
    }


def extract_logic_method(doc: Dict[str, Any]) -> Optional[str]:
    """
    NO guessing:
    - If a canon yaml explicitly declares logic_method, use it.
    - Else return None and mark gap.
    """
    lm = doc.get("logic_method")
    if isinstance(lm, str) and lm.strip():
        return lm.strip()
    return None


def extract_polarity(doc: Dict[str, Any]) -> Optional[str]:
    """
    NO guessing:
    - If a canon yaml explicitly declares polarity, use it.
    - Else None and mark gap.
    """
    p = doc.get("polarity")
    if isinstance(p, str) and p.strip():
        return p.strip()
    return None


def extract_fallback(doc: Dict[str, Any]) -> Optional[str]:
    """
    NO guessing:
    - If a canon yaml declares derivation.fallback or fallback, use it.
    - Else None.
    """
    fb = _get(doc, "derivation.fallback")
    if isinstance(fb, str) and fb.strip():
        return fb.strip()
    fb2 = doc.get("fallback")
    if isinstance(fb2, str) and fb2.strip():
        return fb2.strip()
    return None


# -------------------------
# Registry model & gaps
# -------------------------

def build_metric_spec(doc: Dict[str, Any], path: str) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Returns (spec, gaps)
    - spec follows HP_METRIC_SPEC_V1 properties subset
    - gaps reports missing fields without inventing values
    """
    gaps: Dict[str, Any] = {"path": path, "missing": [], "notes": []}

    metric_id = extract_metric_id(doc)
    if not metric_id:
        gaps["missing"].append("metric_id")
        return None, gaps

    requires_signals = extract_requires_signals(doc)
    requires_metrics = extract_requires_metrics(doc)
    fallback = extract_fallback(doc)

    logic_method = extract_logic_method(doc)
    if logic_method is None:
        gaps["missing"].append("logic_method")

    polarity = extract_polarity(doc)
    if polarity is None:
        gaps["missing"].append("polarity")

    citations = extract_citations(doc)
    # validation_method might be empty; that's allowed but flagged
    if len(citations.get("supporting_definition", [])) == 0:
        gaps["notes"].append("citations.supporting_definition empty")
    if len(citations.get("validation_method", [])) == 0:
        gaps["notes"].append("citations.validation_method empty")

    scopes = extract_scopes(doc)
    if len(scopes) == 0:
        gaps["notes"].append("scopes empty (analysis_modules has no true fields)")

    spec = {
        "contract_id": "HP_METRIC_SPEC_V1",
        "metric_id": metric_id,
        "derivation": {
            "requires_signals": requires_signals,
            "requires_metrics": requires_metrics,
            "fallback": fallback,
        },
        "logic_method": logic_method,
        "polarity": polarity,
        "citations": citations,
        "scopes": scopes,
        "source": {
            "canon_path": path,
            "canon_version": _get(doc, "metadata.version"),
            "canon_category": _get(doc, "metadata.category"),
            "canon_subcategory": _get(doc, "metadata.subcategory"),
        },
        # Fail-closed registry status (NO guessing):
        # - If required contract fields missing -> BLOCKED
        "status": "BLOCKED" if any(k in gaps["missing"] for k in ["logic_method", "polarity"]) else "READY",
        "spec_gaps": gaps,
    }
    return spec, gaps


def build_graph(registry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Graph edges built ONLY from explicit relationships:
    - derivation.requires_metrics
    - enables (if present in canon doc we later extend; currently absent here)
    For now: requires_metrics edges only.
    """
    nodes = sorted(list(registry["metrics"].keys()))
    edges: List[Dict[str, Any]] = []

    for mid, spec in registry["metrics"].items():
        reqm = spec.get("derivation", {}).get("requires_metrics", []) or []
        for dep in reqm:
            edges.append({"type": "requires_metric", "from": mid, "to": dep})

    return {
        "contract_id": "HP_METRIC_GRAPH_V1",
        "nodes": nodes,
        "edges": edges,
    }


def build_registry(canon_dir: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    metric_files = sorted(glob.glob(os.path.join(canon_dir, "**", "*.yaml"), recursive=True))
    metrics: Dict[str, Any] = {}
    gaps: List[Dict[str, Any]] = []

    for p in metric_files:
        doc = read_yaml(p)
        spec, g = build_metric_spec(doc, p)
        if spec is None:
            gaps.append(g)
            continue
        mid = spec["metric_id"]
        if mid in metrics:
            # Fail-closed: duplicates are hard error signals in registry output
            gaps.append({"path": p, "missing": [], "notes": [f"duplicate metric_id: {mid}"]})
            continue
        metrics[mid] = spec
        if g.get("missing") or g.get("notes"):
            gaps.append(g)

    registry = {
        "contract_id": "HP_METRIC_REGISTRY_V1",
        "canon_dir": canon_dir,
        "metrics": metrics,
        "gaps": gaps,
        "counts": {
            "total_metrics": len(metrics),
            "blocked": sum(1 for _, s in metrics.items() if s.get("status") == "BLOCKED"),
            "ready": sum(1 for _, s in metrics.items() if s.get("status") == "READY"),
        },
    }
    graph = build_graph(registry)
    return registry, graph


def main() -> None:
    ap = argparse.ArgumentParser(description="Build HP metric registry + graph from canon YAML")
    ap.add_argument("--canon-dir", default="canon/metrics", help="Canon metrics directory")
    ap.add_argument("--out-registry", default="engine/metrics/registry.json", help="Output registry JSON")
    ap.add_argument("--out-graph", default="engine/metrics/metric_graph.json", help="Output graph JSON")
    args = ap.parse_args()

    registry, graph = build_registry(args.canon_dir)
    write_json(registry, args.out_registry)
    write_json(graph, args.out_graph)


if __name__ == "__main__":
    main()