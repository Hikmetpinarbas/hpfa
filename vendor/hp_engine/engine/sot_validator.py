from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "WARN"  # WARN | ERROR


class SOTValidator:
    """
    Contract-first gate.

    Core rules:
      - NO silent dropping rows.
      - 0.0 is valid.
      - Produce a Data Quality Report + (optionally) transformed dataframe.
    """

    def __init__(self, provider_contract: str = "sportsbase") -> None:
        self.provider_contract = provider_contract

        # Canonical event schema (minimum viable)
        self.required_columns = [
            "team_id",
            "event_type",
            "timestamp_s",
            "x",
            "y",
        ]

        self.pitch = (105.0, 68.0)

    def validate(self, df: pd.DataFrame) -> Tuple[Dict, pd.DataFrame]:
        issues: List[ValidationIssue] = []

        missing = [c for c in self.required_columns if c not in df.columns]
        if missing:
            issues.append(
                ValidationIssue(
                    code="MISSING_REQUIRED_COLUMNS",
                    message=f"Missing required columns: {missing}",
                    severity="ERROR",
                )
            )

        # Null map (explicit)
        null_map = df.isnull().sum().to_dict()

        # Coordinate bounds check (flag only; do not drop)
        if "x" in df.columns:
            x = pd.to_numeric(df["x"], errors="coerce")
            out_x = ((x < -1) | (x > self.pitch[0] + 1)).sum()
            if out_x > 0:
                issues.append(
                    ValidationIssue(
                        code="COORD_OUT_OF_BOUNDS_X",
                        message=f"{int(out_x)} rows have x outside expected pitch bounds (0..{self.pitch[0]}).",
                        severity="WARN",
                    )
                )

        if "y" in df.columns:
            y = pd.to_numeric(df["y"], errors="coerce")
            out_y = ((y < -1) | (y > self.pitch[1] + 1)).sum()
            if out_y > 0:
                issues.append(
                    ValidationIssue(
                        code="COORD_OUT_OF_BOUNDS_Y",
                        message=f"{int(out_y)} rows have y outside expected pitch bounds (0..{self.pitch[1]}).",
                        severity="WARN",
                    )
                )

        if "timestamp_s" in df.columns:
            ts = pd.to_numeric(df["timestamp_s"], errors="coerce")
            neg = (ts < 0).sum()
            if neg > 0:
                issues.append(
                    ValidationIssue(
                        code="NEGATIVE_TIMESTAMP",
                        message=f"{int(neg)} rows have negative timestamp_s.",
                        severity="WARN",
                    )
                )

        status = "HEALTHY"
        if any(i.severity == "ERROR" for i in issues):
            status = "BLOCKED"
        elif any(i.severity == "WARN" for i in issues):
            status = "DEGRADED"

        report = {
            "status": status,
            "provider": self.provider_contract,
            "issues": [i.__dict__ for i in issues],
            "null_map": null_map,
            "row_count": int(len(df)),
            "columns": list(df.columns),
        }

        return report, df