from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from canon.definitions.master_schema import SchemaSpec, load_schema, default_schema_path


@dataclass
class ValidationReport:
    schema_version: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    quarantined_rows: int = 0

    def ok(self) -> bool:
        return len(self.errors) == 0


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2]


def _quarantine_dir() -> Path:
    # repo_root/data/quarantine
    return _repo_root() / "data" / "quarantine"


def write_quarantine_csv(dfq: pd.DataFrame, reason: str) -> Path:
    qdir = _quarantine_dir()
    qdir.mkdir(parents=True, exist_ok=True)
    ts = _utc_stamp()
    out = qdir / f"quarantine_{reason}_{ts}.csv"
    dfq.to_csv(out, index=False)
    # manifest append
    manifest = qdir / "manifest.log"
    with manifest.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{out.name}\treason={reason}\trows={len(dfq)}\n")
    return out


def _ensure_columns_present(df: pd.DataFrame, required_cols: List[str]) -> List[str]:
    missing = [c for c in required_cols if c not in df.columns]
    return missing


def _coerce_column(df: pd.DataFrame, col: str, target: str, nullable: bool, report: ValidationReport) -> None:
    # Minimal coercion rules. Fail-closed on non-nullable critical coercion loss.
    if col not in df.columns:
        return

    s = df[col]

    try:
        if target == "string":
            df[col] = s.astype("string")
            return

        if target == "bool":
            # accept True/False, 1/0, "true"/"false"
            mapped = s.map(
                lambda v: v if isinstance(v, bool) else
                (True if str(v).strip().lower() in ("1", "true", "t", "yes", "y") else
                 False if str(v).strip().lower() in ("0", "false", "f", "no", "n") else pd.NA)
            )
            # coercion loss check
            loss = mapped.isna() & ~s.isna()
            if loss.any() and not nullable:
                report.errors.append(f"Critical: bool coercion loss in '{col}' ({int(loss.sum())} rows).")
                return
            df[col] = mapped.astype("boolean")
            return

        if target in ("float64", "int64"):
            coerced = pd.to_numeric(s, errors="coerce")
            loss = coerced.isna() & ~s.isna()
            if loss.any() and not nullable:
                report.errors.append(f"Critical: numeric coercion loss in '{col}' ({int(loss.sum())} rows).")
                return
            if target == "int64":
                # keep as pandas nullable integer
                df[col] = coerced.round().astype("Int64")
            else:
                df[col] = coerced.astype("Float64")
            return

        if target.startswith("enum:"):
            # keep enum values as canonical uppercase strings
            df[col] = s.astype("string").str.upper()
            return

        # fallback: treat unknown dtype as string
        report.warnings.append(f"Unknown dtype '{target}' for '{col}', coerced to string.")
        df[col] = s.astype("string")

    except Exception as e:
        report.errors.append(f"Critical: failed coercion for '{col}' to '{target}': {e}")


def _enforce_enum(df: pd.DataFrame, col: str, enum_spec: Dict[str, Any], report: ValidationReport) -> Tuple[pd.Series, pd.Series]:
    """
    Returns: (normalized_series, unmapped_mask)
    """
    s = df[col].astype("string").str.upper()
    canonical = set(str(x).upper() for x in enum_spec["canonical"])
    fallback = str(enum_spec["fallback"]).upper()

    unmapped_mask = (~s.isna()) & (~s.isin(list(canonical)))
    # preserve provenance: set unmapped to UNMAPPED_ENUM (then quarantine + degrade)
    s2 = s.copy()
    s2.loc[unmapped_mask] = "UNMAPPED_ENUM"
    # still ensure nulls become fallback (epistemic degrade)
    s2 = s2.fillna(fallback)
    return s2, unmapped_mask


def check_contract(df: pd.DataFrame, schema: SchemaSpec | None = None) -> Tuple[pd.DataFrame, ValidationReport]:
    """
    Fail-closed rules:
      - Missing required group columns => hard error
      - Non-nullable coercion loss => hard error
      - Coordinates/time/phase constraints violation => hard error
    No-drop rules:
      - No row deletion.
      - Unmapped enums => quarantine + degrade + audit_flag=True + popper_tag=LOW_CONFIDENCE
      - Nulls in nullable columns allowed; nulls in non-nullable => hard error (after coercion)
    """
    if schema is None:
        schema = load_schema(default_schema_path())

    report = ValidationReport(schema_version=schema.schema_version)
    cols = schema.flat_columns()

    # 1) Required columns presence (atomic groups)
    missing = _ensure_columns_present(df, schema.required_columns())
    if missing:
        report.errors.append(f"Critical: missing required columns: {missing}")
        return df, report

    # 2) Coerce types (critical losses become errors)
    for col_name, spec in cols.items():
        _coerce_column(df, col_name, spec.dtype, spec.nullable, report)

    if not report.ok():
        return df, report

    # 3) Enforce enums + quarantine policy
    # Ensure Validator columns exist (even if upstream didn't set)
    if "audit_flag" not in df.columns:
        df["audit_flag"] = False
    if "popper_tag" not in df.columns:
        df["popper_tag"] = "LOW_CONFIDENCE"

    # action_type enum
    if "action_type" in df.columns:
        norm, unmapped = _enforce_enum(df, "action_type", schema.enums["action_type"].__dict__, report)
        df["action_type"] = norm
        if unmapped.any():
            q = df.loc[unmapped].copy()
            q["quarantine_reason"] = "UNMAPPED_ACTION_TYPE"
            write_quarantine_csv(q, "UNMAPPED_ACTION_TYPE")
            # degrade epistemically but do not delete
            df.loc[unmapped, "audit_flag"] = True
            df.loc[unmapped, "popper_tag"] = "LOW_CONFIDENCE"
            df.loc[unmapped, "action_type"] = schema.enums["action_type"].fallback

            report.warnings.append(f"Unmapped action_type rows quarantined: {int(unmapped.sum())}")
            report.quarantined_rows += int(unmapped.sum())

    # popper_tag enum
    if "popper_tag" in df.columns:
        norm, unmapped = _enforce_enum(df, "popper_tag", schema.enums["epistemic_tag"].__dict__, report)
        df["popper_tag"] = norm
        if unmapped.any():
            q = df.loc[unmapped].copy()
            q["quarantine_reason"] = "UNMAPPED_POPPER_TAG"
            write_quarantine_csv(q, "UNMAPPED_POPPER_TAG")
            df.loc[unmapped, "audit_flag"] = True
            df.loc[unmapped, "popper_tag"] = schema.enums["epistemic_tag"].fallback
            report.warnings.append(f"Unmapped popper_tag rows quarantined: {int(unmapped.sum())}")
            report.quarantined_rows += int(unmapped.sum())

    # 4) Non-nullable fields must be non-null (post-coercion)
    non_nullable_cols = [c.name for c in cols.values() if not c.nullable]
    null_viol = [c for c in non_nullable_cols if df[c].isna().any()]
    if null_viol:
        report.errors.append(f"Critical: nulls in non-nullable columns: {null_viol}")
        return df, report

    # 5) Constraints (fail-closed)
    c = schema.constraints
    x_max = float(c["pitch"]["x_max"])
    y_max = float(c["pitch"]["y_max"])
    eps = float(c["pitch"]["epsilon"])

    if (df["x_norm"].astype(float).max() > x_max + eps) or (df["x_norm"].astype(float).min() < -eps):
        report.errors.append("Critical: x_norm outside pitch ontology.")
        return df, report
    if (df["y_norm"].astype(float).max() > y_max + eps) or (df["y_norm"].astype(float).min() < -eps):
        report.errors.append("Critical: y_norm outside pitch ontology.")
        return df, report

    tmin = float(c["time"]["timestamp_min"])
    tmax = float(c["time"]["timestamp_max"])
    if (df["timestamp"].astype(float).min() < tmin) or (df["timestamp"].astype(float).max() > tmax):
        report.errors.append("Critical: timestamp outside allowed range.")
        return df, report

    pmin = int(c["phase"]["min"])
    pmax = int(c["phase"]["max"])
    if (df["phase_id"].astype(int).min() < pmin) or (df["phase_id"].astype(int).max() > pmax):
        report.errors.append("Critical: phase_id outside 1-6 range.")
        return df, report

    return df, report
