from __future__ import annotations

from typing import Any, Dict, List


class PopperGate:
    """
    Minimal Popper gate (v1).

    Goals:
      - Convert raw metric values into explicit CLAIM objects.
      - Detect basic contradictions between core pressing metrics.
      - Enforce "needs evidence" when a claim has no supporting metric.

    Next step (v2):
      - Read falsifiability blocks from registry YAML (H0/H1/supports/contradicts).
    """

    def verify(self, features: Dict[str, Any], registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        claims: List[Dict[str, Any]] = []

        # 1) Build baseline claims
        for key, meta in registry.items():
            metric_name = meta.get("metric_name", key)
            val = features.get(key)

            # If compute layer already returned structured status, pass-through.
            if isinstance(val, dict) and "status" in val:
                claims.append({"metric": key, "metric_name": metric_name, **val})
                continue

            if val is None:
                claims.append(
                    {
                        "metric": key,
                        "metric_name": metric_name,
                        "status": "BLOCKED",
                        "reason": "NO_VALUE",
                        "notes": [],
                    }
                )
                continue

            # Numeric value -> VERIFIED (for now)
            claims.append(
                {
                    "metric": key,
                    "metric_name": metric_name,
                    "status": "VERIFIED",
                    "value": val,
                    "interpretation": "ok",
                    "notes": [],
                }
            )

        # 2) Contradiction checks (pressing triad)
        v_ppda = _get_verified_value(claims, "ppda")
        v_pi = _get_verified_value(claims, "pressing_intensity")

        if v_ppda is not None and v_pi is not None:
            # Placeholder thresholds. Later: contextual benchmarks.
            if v_ppda > 12 and v_pi > 25:
                _flag_conflict(
                    claims,
                    "ppda",
                    reason="CONTRADICTION_WITH_PRESSING_INTENSITY",
                    note="PPDA suggests weak press, but pressing_intensity suggests high press. Check mapping/definitions.",
                )
            if v_ppda < 8 and v_pi < 10:
                _flag_conflict(
                    claims,
                    "ppda",
                    reason="CONTRADICTION_WITH_PRESSING_INTENSITY",
                    note="PPDA suggests strong press, but pressing_intensity suggests low press. Check defensive_actions mapping.",
                )

        # 3) Unfalsifiable (v1 strictness): require at least one supporting metric
        support_map = {
            "ppda": ["pressing_intensity"],
            "field_tilt": ["ppda"],
            "pressing_intensity": ["ppda"],
        }

        verified_keys = {c["metric"] for c in claims if c.get("status") == "VERIFIED"}
        for c in claims:
            if c.get("status") != "VERIFIED":
                continue
            k = c["metric"]
            supports = support_map.get(k, [])
            if supports and not any(s in verified_keys for s in supports):
                c["status"] = "NEEDS_EVIDENCE"
                c["reason"] = "NO_SUPPORTING_METRIC"
                c.setdefault("notes", []).append(f"Requires one of: {supports}")

        return claims


def _get_verified_value(claims: List[Dict[str, Any]], metric_key: str):
    for c in claims:
        if c.get("metric") == metric_key and c.get("status") == "VERIFIED":
            return c.get("value")
    return None


def _flag_conflict(claims: List[Dict[str, Any]], metric_key: str, reason: str, note: str) -> None:
    for c in claims:
        if c.get("metric") == metric_key and c.get("status") == "VERIFIED":
            c["status"] = "CONFLICT"
            c["reason"] = reason
            c.setdefault("notes", []).append(note)