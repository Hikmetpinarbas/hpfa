from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import re, csv
from .raw_model import RawTable, RawColumn, RawCellType

def _sniff_ext(path: str) -> str:
    p = path.lower()
    if p.endswith(".csv"): return "csv"
    if p.endswith(".xlsx") or p.endswith(".xlsm") or p.endswith(".xls"): return "xlsx"
    if p.endswith(".xml"): return "xml"
    return "unknown"

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _infer(values: List[Any]) -> RawCellType:
    nonnull = [v for v in values if v is not None and str(v).strip() != ""]
    if not nonnull: return RawCellType.UNKNOWN
    sample = nonnull[:40]

    b = 0
    for v in sample:
        if isinstance(v, bool): b += 1
        elif str(v).strip().lower() in {"true","false","0","1","yes","no","evet","hayır","hayir"}: b += 1
    if b/len(sample) >= 0.9: return RawCellType.BOOL

    n = 0
    for v in sample:
        if isinstance(v, (int,float)): n += 1
        else:
            t = str(v).strip().replace(",", ".")
            try: float(t); n += 1
            except Exception: pass
    if n/len(sample) >= 0.9: return RawCellType.NUMBER

    d = 0
    for v in sample:
        t = str(v).strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}$", t): d += 1
        elif re.match(r"^\d{2}[./-]\d{2}[./-]\d{2,4}$", t): d += 1
    if d/len(sample) >= 0.9: return RawCellType.DATE

    return RawCellType.STRING

def _read_csv(path: str, encoding: Optional[str], delimiter: Optional[str]) -> RawTable:
    p = Path(path)
    enc = encoding or "utf-8"
    warnings: List[str] = []

    delim = delimiter
    if delim is None:
        try:
            head = p.read_text(encoding=enc, errors="replace").splitlines()[:5]
            joined = "\n".join(head)
            cands = [",",";","\t","|"]
            scores = {c: joined.count(c) for c in cands}
            delim = max(scores, key=scores.get) if max(scores.values()) > 0 else ","
        except Exception:
            delim = ","
            warnings.append("csv_delimiter_sniff_failed_default_comma")

    rows: List[Dict[str, Any]] = []
    with p.open("r", encoding=enc, errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=delim)
        all_rows = list(reader)

    if not all_rows:
        return RawTable(format="csv", source=str(p), table_name=p.name, columns=[], rows=[],
                        warnings=warnings+["csv_empty"], provenance={"encoding":enc,"delimiter":delim})

    header = all_rows[0]
    cols = [RawColumn(name=_norm(h), source_name=h) for h in header]

    for ridx, r in enumerate(all_rows[1:], start=1):
        rec: Dict[str, Any] = {"__rownum": ridx}
        for i, c in enumerate(cols):
            rec[c.name] = r[i] if i < len(r) else ""
        # KAYIPSIZ: fazla hücre varsa da sakla
        if len(r) > len(cols):
            rec["__overflow__"] = r[len(cols):]
        rows.append(rec)

    for c in cols:
        c.inferred_type = _infer([row.get(c.name) for row in rows])

    return RawTable(format="csv", source=str(p), table_name=p.name, columns=cols, rows=rows,
                    warnings=warnings, provenance={"encoding":enc,"delimiter":delim})

def _read_xlsx(path: str, sheet: Optional[str], header_row: int) -> RawTable:
    import pandas as pd
    p = Path(path)
    warnings: List[str] = []

    xl = pd.ExcelFile(p)
    sh = sheet or (xl.sheet_names[0] if xl.sheet_names else "Sheet1")
    if sheet is None:
        warnings.append("xlsx_sheet_default_first")

    hdr0 = max(0, int(header_row) - 1)
    df = pd.read_excel(p, sheet_name=sh, header=hdr0)
    df = df.dropna(how="all")
    df.columns = [_norm(str(c)) for c in df.columns]

    rows = df.where(df.notna(), "").to_dict(orient="records")
    for i, r in enumerate(rows, start=1):
        r["__rownum"] = i

    cols = [RawColumn(name=str(c), source_name=str(c)) for c in df.columns]
    for c in cols:
        c.inferred_type = _infer([row.get(c.name) for row in rows])

    return RawTable(format="xlsx", source=str(p), table_name=str(sh),
                    columns=cols, rows=rows, warnings=warnings,
                    provenance={"sheet":sh,"header_row":header_row,"sheets":xl.sheet_names})

def _read_xml(path: str, entity_path: str) -> RawTable:
    import xml.etree.ElementTree as ET
    p = Path(path)
    warnings: List[str] = []

    tree = ET.parse(p)
    root = tree.getroot()

    parts = [x for x in entity_path.strip("/").split("/") if x]
    if not parts:
        raise ValueError("XML requires entity_path (record boundary).")

    def tag_eq(tag: str, name: str) -> bool:
        return tag == name or tag.endswith("}"+name)

    nodes = [root]
    for name in parts:
        nxt=[]
        for n in nodes:
            for ch in list(n):
                if tag_eq(ch.tag, name):
                    nxt.append(ch)
        nodes = nxt
        if not nodes:
            warnings.append(f"xml_entity_path_not_found_at:{name}")
            break

    entities = nodes
    colnames: List[str] = []
    rows: List[Dict[str, Any]] = []

    def add_col(k: str):
        if k not in colnames:
            colnames.append(k)

    for i, e in enumerate(entities, start=1):
        row: Dict[str, Any] = {"__rownum": i}
        # attributes
        for k,v in e.attrib.items():
            kk = _norm(k)
            row[kk] = v
            add_col(kk)
        # direct children text
        for ch in list(e):
            k = _norm(ch.tag.split("}")[-1])
            txt = (ch.text or "").strip()
            # KAYIPSIZ: boş da olsa kolon tanımlı kalsın
            row.setdefault(k, txt)
            add_col(k)
        rows.append(row)

    cols = [RawColumn(name=c, source_name=c) for c in colnames]
    for c in cols:
        c.inferred_type = _infer([row.get(c.name) for row in rows])

    return RawTable(format="xml", source=str(p), table_name=parts[-1],
                    columns=cols, rows=rows, warnings=warnings,
                    provenance={"entity_path":entity_path,"entity_count":len(entities)})

def read_any(path: str, *, fmt: Optional[str]=None,
             encoding: Optional[str]=None, delimiter: Optional[str]=None,
             sheet: Optional[str]=None, header_row: int=1,
             entity_path: Optional[str]=None) -> RawTable:
    f = fmt or _sniff_ext(path)
    if f == "csv":  return _read_csv(path, encoding, delimiter)
    if f == "xlsx": return _read_xlsx(path, sheet, header_row)
    if f == "xml":
        if not entity_path: raise ValueError("XML requires entity_path.")
        return _read_xml(path, entity_path)
    raise ValueError(f"Unknown format: {f}. Provide fmt=csv|xlsx|xml.")
