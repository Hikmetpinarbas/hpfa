#!/usr/bin/env python3
import argparse, csv, datetime, glob, json, os, re
from xml.etree import ElementTree as ET
import openpyxl

PLAYER_ID_RE = re.compile(r"\((\d+)\)")
TEAM_METRIC_RE = re.compile(r"^(?P<tname>.+?)\s*\((?P<tid>\d+)\)\s*-\s*(?P<metric>.+)$")

def safe_float(v):
    if v is None: return None
    s = str(v).strip()
    if not s: return None
    s = s.replace(",", ".")
    try: return float(s)
    except: return None

def safe_int(v):
    if v is None: return None
    s = str(v).strip()
    if not s: return None
    try: return int(float(s))
    except: return None

def parse_player_id(code: str):
    m = PLAYER_ID_RE.search(code or "")
    return int(m.group(1)) if m else None

def parse_team_id(team_raw: str):
    m = PLAYER_ID_RE.search(team_raw or "")
    return int(m.group(1)) if m else None

def read_csv_rows(path: str, delimiter: str = ";"):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
        return reader.fieldnames or [], rows

def infer_stream_from_csv(fieldnames, nrows, sample_codes):
    fields = [f.strip() for f in (fieldnames or [])]
    has_team = "team" in fields
    if (not has_team) and ("code" in fields) and any((" - " in (c or "") and "(" in (c or "")) for c in sample_codes):
        return "team_metric"
    if has_team and nrows > 500:
        return "outfield"
    if has_team and 50 <= nrows <= 300:
        return "gk"
    return "unknown"

def read_xml_instances(path: str):
    tree = ET.parse(path)
    root = tree.getroot()
    insts = []
    for inst in root.iter("instance"):
        d = {}
        for tag in ["ID", "start", "end", "code", "label"]:
            el = inst.find(tag)
            d[tag.lower()] = (el.text.strip() if (el is not None and el.text) else None)
        d["id"] = safe_int(d.get("id"))
        d["start"] = safe_float(d.get("start"))
        d["end"] = safe_float(d.get("end"))
        insts.append(d)
    return insts

def sample_event_keys_from_csv(rows, limit=800):
    keys = set()
    for r in rows[:limit]:
        s = safe_float(r.get("start"))
        e = safe_float(r.get("end"))
        c = (r.get("code") or "").strip()
        if s is None or e is None or not c:
            continue
        keys.add((round(s, 2), round(e, 2), c))
    return keys

def sample_event_keys_from_xml(insts, limit=800):
    keys = set()
    for d in insts[:limit]:
        s = safe_float(d.get("start"))
        e = safe_float(d.get("end"))
        c = (d.get("code") or "").strip()
        if s is None or e is None or not c:
            continue
        keys.add((round(s, 2), round(e, 2), c))
    return keys

def pair_xml_to_csv(xml_insts, csv_candidates):
    xml_keys = sample_event_keys_from_xml(xml_insts, limit=800)
    best = None
    for csv_path, rows in csv_candidates:
        csv_keys = sample_event_keys_from_csv(rows, limit=800)
        inter = len(xml_keys & csv_keys)
        if best is None or inter > best["sample_intersection"]:
            best = {"csv_path": csv_path, "sample_intersection": inter}
    return best

def write_jsonl(path: str, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def xlsx_to_json(path: str):
    wb = openpyxl.load_workbook(path, data_only=True)
    out = {}
    for sh in wb.worksheets:
        rows = list(sh.iter_rows(values_only=True))
        header_row_idx = None
        for i, row in enumerate(rows[:50]):
            non_empty = sum(1 for x in row if x not in (None, ""))
            if non_empty >= 5:
                header_row_idx = i
                break
        if header_row_idx is None:
            continue
        headers = [str(x).strip() if x is not None else "" for x in rows[header_row_idx]]
        headers = [h if h else f"col{j+1}" for j, h in enumerate(headers)]
        data = []
        for row in rows[header_row_idx + 1:]:
            if all(x in (None, "") for x in row):
                continue
            rec = {}
            for j, h in enumerate(headers):
                val = row[j] if j < len(row) else None
                if isinstance(val, (datetime.datetime, datetime.date)):
                    val = val.isoformat()
                rec[h] = val
            data.append(rec)
        out[sh.title] = data
    return out

def canonical_from_csv(match_id: str, stream: str, rows):
    recs = []
    for r in rows:
        code = (r.get("code") or "").strip() or None
        team_raw = (r.get("team") or "").strip() or None
        rec = {
            "match_id": match_id,
            "stream": stream,
            "id": safe_int(r.get("ID")),
            "t_start": safe_float(r.get("start")),
            "t_end": safe_float(r.get("end")),
            "half": safe_int(r.get("half")),
            "action": (r.get("action") or "").strip() or None,
            "code": code,
            "x": safe_float(r.get("pos_x")),
            "y": safe_float(r.get("pos_y")),
            "team_raw": team_raw,
            "team_id": None,
            "player_id": None,
            "metric": None,
        }
        if stream in ("outfield", "gk"):
            rec["team_id"] = parse_team_id(team_raw)
            rec["player_id"] = parse_player_id(code or "")
        elif stream == "team_metric":
            m = TEAM_METRIC_RE.match(code or "")
            if m:
                rec["team_id"] = int(m.group("tid"))
                rec["team_raw"] = f"{m.group('tname').strip()} ({m.group('tid')})"
                rec["metric"] = m.group("metric").strip()
        recs.append(rec)
    return recs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    in_dir, out_dir, match_id = args.in_dir, args.out_dir, args.match_id
    csv_files = sorted(glob.glob(os.path.join(in_dir, "*.csv")))
    xml_files = sorted(glob.glob(os.path.join(in_dir, "*.xml")))
    xlsx_files = sorted(glob.glob(os.path.join(in_dir, "*.xlsx")))

    if not csv_files:
        raise SystemExit("ERROR: No CSV files found in --in-dir")

    os.makedirs(out_dir, exist_ok=True)

    index = {
        "match_id": match_id,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "inputs": {},
        "pairing": {},
        "outputs": {},
    }

    csv_cache = {}
    written_streams = set()

    for p in csv_files:
        fieldnames, rows = read_csv_rows(p, delimiter=";")
        csv_cache[p] = (fieldnames, rows)
        sample_codes = [(r.get("code") or "") for r in rows[:50]]
        stream = infer_stream_from_csv(fieldnames, len(rows), sample_codes)

        index["inputs"][os.path.basename(p)] = {"type":"csv","stream":stream,"n_rows":len(rows),"columns":fieldnames}

        recs = canonical_from_csv(match_id, stream, rows)
        out_name = f"canonical_{stream}.jsonl"
        out_path = os.path.join(out_dir, out_name)
        if stream in written_streams:
            stem = os.path.splitext(os.path.basename(p))[0].replace(" ", "_")
            out_path = os.path.join(out_dir, f"canonical_{stream}__{stem}.jsonl")
        written_streams.add(stream)

        write_jsonl(out_path, recs)
        index["outputs"][os.path.basename(out_path)] = out_path

    if xml_files:
        csv_candidates = [(p, csv_cache[p][1]) for p in csv_files]
        for xp in xml_files:
            insts = read_xml_instances(xp)
            best = pair_xml_to_csv(insts, csv_candidates)
            index["pairing"][os.path.basename(xp)] = {
                "n_instances": len(insts),
                "paired_csv": os.path.basename(best["csv_path"]) if best else None,
                "sample_intersection": best["sample_intersection"] if best else None,
            }
            out = [{"match_id": match_id, "xml_file": os.path.basename(xp), **d} for d in insts]
            out_path = os.path.join(out_dir, f"xml_{len(insts)}__{os.path.basename(xp)}.jsonl")
            write_jsonl(out_path, out)
            index["outputs"][os.path.basename(out_path)] = out_path

    for xp in xlsx_files:
        data = xlsx_to_json(xp)
        index["inputs"][os.path.basename(xp)] = {"type":"xlsx","sheets":list(data.keys()),"n_rows_by_sheet":{k:len(v) for k,v in data.items()}}
        for sh, rows in data.items():
            out_path = os.path.join(out_dir, f"stats__{os.path.basename(xp)}__{sh}.jsonl")
            write_jsonl(out_path, [{"match_id": match_id, "sheet": sh, **r} for r in rows])
            index["outputs"][os.path.basename(out_path)] = out_path

    with open(os.path.join(out_dir, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print("OK ✅")
    print("OUT:", out_dir)
    print("PAIRING:")
    for k,v in index["pairing"].items():
        print("-", k, "->", v.get("paired_csv"), "inter=", v.get("sample_intersection"))

if __name__ == "__main__":
    main()
