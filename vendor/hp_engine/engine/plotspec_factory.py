from __future__ import annotations

from typing import Any, Dict, List


class PlotSpecFactory:
    """
    Generates PlotSpec JSON-like dictionaries for the UI layer.

    Rule:
      - Engine produces specs; UI renders.
      - This avoids heavy plotting in core (prevents file storms).
    """

    def generate(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        specs: List[Dict[str, Any]] = []
        for c in claims:
            if c.get("status") != "VERIFIED":
                continue

            metric = (c.get("metric") or "").lower()
            if metric in ("ppda",):
                specs.append(self._single_value("PPDA", c, unit="ratio"))
            elif metric in ("field_tilt", "field tilt"):
                specs.append(self._single_value("Field Tilt", c, unit="pct"))
            elif metric in ("pressing_intensity", "pressing intensity"):
                specs.append(self._single_value("Pressing Intensity", c, unit="actions/90"))
        return specs

    def _single_value(self, title: str, claim: Dict[str, Any], unit: str) -> Dict[str, Any]:
        return {
            "type": "SingleValue",
            "title": title,
            "value": claim.get("value"),
            "unit": unit,
            "status": claim.get("status"),
            "notes": claim.get("notes", []),
        }