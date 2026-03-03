from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import re
import json
import os

from .raw_model import RawTable


@dataclass
class CanonicalSchema:
    fields: Dict[str, str]          # canonical_field -> type
    required: List[str] = field(default_factory=list)


@dataclass
class ImportProfile:
    mapping: Dict[str, str]         # source_field -> canonical_field
    decimal: str = "."
    day_first: bool = True
    strict_required: bool = True    # if True: missing required -> BLOCK
    keep_extras: bool = True        # if True: NEVER DROP unmapped columns
    defaults: Dict[str, Any] = field(default_factory=dict)  # canonical_field -> default literal or "$ENV"


@dataclass
class CanonicalTable:
    schema_name: str
    source: str
    rows: List[Dict[str, Any]]
    warnings: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


def _nk(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def _env_expand(v: Any) -> Any:
    # deterministic env expansion:
    # if value is "$VARNAME" and env exists -> replace; else keep literal.
    if isinstance(v, str) and len(v) >= 2 and v.startswith("$"):
        key = v[1:]
        return os.environ.get(key, v)
    return v


def _coerce(v: Any, t: str, profile: ImportProfile) -> Any:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    tt = (t or "string").lower()

    if tt == "string":
        return s
    if tt == "bool":
        sl = s.lower()
        if sl in {"true", "1", "yes", "y", "evet"}:
            return True
        if sl in {"false", "0", "no", "n", "hayır", "hayir"}:
            return False
        return None
    if tt == "number":
        ss = s
        if profile.decimal == ",":
            ss = ss.replace(".", "").replace(",", ".")
        else:
            ss = ss.replace(",", "")
        try:
            return float(ss)
        except Exception:
            return None
    if tt in {"date", "datetime"}:
        return s
    return s


def _apply_defaults(row: Dict[str, Any], schema: CanonicalSchema, profile: ImportProfile) -> None:
    if not profile.defaults:
        return
    for canon_key, dv in profile.defaults.items():
        if canon_key not in schema.fields:
            continue
        v = row.get(canon_key)
        if v is None or str(v).strip() == "":
            dv2 = _env_expand(dv)
            row[canon_key] = _coerce(dv2, schema.fields.get(canon_key, "string"), profile)


def canonicalize(
    raw: RawTable,
    schema: CanonicalSchema,
    profile: ImportProfile,
    schema_name: str = "hp_cdl",
) -> CanonicalTable:
    warnings: List[str] = []

    # normalize mapping keys
    m = {_nk(k): v for k, v in (profile.mapping or {}).items()}

    # raw_col_name -> canonical_field
    col_map: Dict[str, str] = {}
    for c in raw.columns:
        k = _nk(c.name)
        if k in m:
            col_map[c.name] = m[k]

    unmapped = [c.name for c in raw.columns if c.name not in col_map]
    if unmapped:
        warnings.append(f"unmapped_columns:{len(unmapped)}")

    out_rows: List[Dict[str, Any]] = []
    extras_total_kv = 0

    for i, r in enumerate(raw.rows):
        out: Dict[str, Any] = {}

        # map known -> canonical
        for src, canon in col_map.items():
            out[canon] = _coerce(r.get(src), schema.fields.get(canon, "string"), profile)

        # ensure all schema fields exist
        for canon in schema.fields.keys():
            out.setdefault(canon, None)

        # apply deterministic defaults
        _apply_defaults(out, schema, profile)

        # NO-DROP: keep unmapped as deterministic JSON in __extras__
        if profile.keep_extras:
            extras: Dict[str, Any] = {}
            for k, v in r.items():
                if k not in col_map:
                    extras[str(k)] = v
            extras_total_kv += len(extras)
            out["__extras__"] = json.dumps(extras, ensure_ascii=False, sort_keys=True)
        else:
            out["__extras__"] = json.dumps({}, ensure_ascii=False, sort_keys=True)

        # row lineage
        out["__rownum__"] = i + 1

        out_rows.append(out)

    # required gate
    if schema.required:
        bad = 0
        for rr in out_rows:
            ok = True
            for req in schema.required:
                v = rr.get(req)
                if v is None or str(v).strip() == "":
                    ok = False
                    break
            if not ok:
                bad += 1

        if bad:
            msg = f"required_missing_rows:{bad}"
            if profile.strict_required:
                raise SystemExit(f"[BLOCK] {msg}")
            warnings.append(msg)

    return CanonicalTable(
        schema_name=schema_name,
        source=raw.source,
        rows=out_rows,
        warnings=warnings,
        evidence={
            "raw_format": raw.format,
            "raw_table": raw.table_name,
            "raw_warnings": raw.warnings,
            "raw_cols": len(raw.columns),
            "raw_rows": len(raw.rows),
            "mapped_cols": len(col_map),
            "extras_total_kv": extras_total_kv,
            "keep_extras": bool(profile.keep_extras),
            "strict_required": bool(profile.strict_required),
            "defaults_keys": sorted(list((profile.defaults or {}).keys()))[:50],
        },
    )
