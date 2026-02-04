from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


_NUM_RE = re.compile(r"\d+")
_WS_RE = re.compile(r"\s+")


def _safe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    if s == "" or s.lower() in {"na", "nan", "null", "none"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def _safe_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"na", "nan", "null", "none"}:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _norm_text(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = _WS_RE.sub(" ", s)
    return s


def _read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _guess_category(action_raw: str) -> str:
    a = action_raw.lower()
    if "şut" in a or "shot" in a or "gol" in a or "goal" in a or "psxg" in a:
        return "SHOT"
    if "pas" in a or "pass" in a or "cross" in a or "orta" in a:
        return "PASS"
    if "mücadele" in a or "challenge" in a or "tackle" in a or "interception" in a or "kapma" in a:
        return "DEFENSE"
    if "kale vuruş" in a or "goal kick" in a or "build" in a or "set hücum" in a or "positional" in a:
        return "BUILDUP"
    if "hata" in a or "mistake" in a or "top kayb" in a or "loss" in a:
        return "MISTAKE"
    if "korner" in a or "corner" in a or "serbest vuruş" in a or "free kick" in a:
        return "SET_PIECE"
    return "OTHER"


@dataclass
class ClipRow:
    source_file: str
    row_id: Optional[int]
    match_id: Optional[str]
    start_s: Optional[float]
    end_s: Optional[float]
    half: Optional[int]
    team_id: Optional[int]
    player_id: Optional[int]
    code_raw: str
    action_raw: str
    action_canonical: str
    action_category: str
    pos_x: Optional[float]
    pos_y: Optional[float]


def iter_csv_files(sample_dir: Path) -> Iterator[Path]:
    for p in sample_dir.rglob("*.csv"):
        if p.is_file():
            yield p


def load_action_mappings(repo_root: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    signal_map = _read_json(repo_root / "canon" / "mappings" / "signal_mappings.json")
    alias_map = _read_json(repo_root / "canon" / "mappings" / "tr_action_aliases.json")

    signal_map = {_norm_text(k): v for k, v in signal_map.items()}
    alias_map = {_norm_text(k): v for k, v in alias_map.items()}
    return signal_map, alias_map


def canonicalize_action(action_raw: str, signal_map: Dict[str, str], alias_map: Dict[str, str]) -> str:
    a = _norm_text(action_raw)
    if a in alias_map:
        aliased = _norm_text(alias_map[a])
        if aliased in signal_map:
            return signal_map[aliased]
        return aliased
    if a in signal_map:
        return signal_map[a]
    return "unmapped"


def parse_row(file_path: Path, row: Dict[str, str], signal_map: Dict[str, str], alias_map: Dict[str, str], match_id: str) -> ClipRow:
    row_id = _safe_int(row.get("ID") or row.get("id"))
    start_s = _safe_float(row.get("start"))
    end_s = _safe_float(row.get("end"))
    half = _safe_int(row.get("half"))

    code_raw = _norm_text(row.get("code", ""))
    action_raw = _norm_text(row.get("action", ""))

    nums = [int(x) for x in _NUM_RE.findall(code_raw)] if code_raw else []
    team_id = nums[0] if len(nums) >= 1 else None
    player_id = nums[1] if len(nums) >= 2 else None

    pos_x = _safe_float(row.get("pos_x"))
    pos_y = _safe_float(row.get("pos_y"))

    action_canonical = canonicalize_action(action_raw, signal_map, alias_map)
    action_category = _guess_category(action_raw) if action_canonical == "unmapped" else _guess_category(action_canonical)

    return ClipRow(
        source_file=str(file_path.as_posix()),
        row_id=row_id,
        match_id=match_id,
        start_s=start_s,
        end_s=end_s,
        half=half,
        team_id=team_id,
        player_id=player_id,
        code_raw=code_raw,
        action_raw=action_raw,
        action_canonical=action_canonical,
        action_category=action_category,
        pos_x=pos_x,
        pos_y=pos_y,
    )


def parse_csv_file(file_path: Path, signal_map: Dict[str, str], alias_map: Dict[str, str]) -> List[ClipRow]:
    match_id = f"{file_path.parent.name}/{file_path.stem}"
    rows: List[ClipRow] = []
    with file_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            rows.append(parse_row(file_path, r, signal_map, alias_map, match_id))
    return rows


def write_jsonl(out_path: Path, rows: Iterable[ClipRow]) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
            n += 1
    return n


def build_summary(all_rows: List[ClipRow]) -> Dict:
    total = len(all_rows)
    actions_raw = Counter(r.action_raw for r in all_rows if r.action_raw)
    actions_canon = Counter(r.action_canonical for r in all_rows if r.action_canonical)
    categories = Counter(r.action_category for r in all_rows if r.action_category)

    mapped = sum(1 for r in all_rows if r.action_canonical and r.action_canonical != "unmapped")
    unmapped = total - mapped

    unmapped_actions = Counter(r.action_raw for r in all_rows if r.action_canonical == "unmapped" and r.action_raw)

    by_match = defaultdict(int)
    for r in all_rows:
        by_match[r.match_id or "unknown_match"] += 1

    return {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "total_rows": total,
        "mapped_rows": mapped,
        "unmapped_rows": unmapped,
        "unique_action_raw": len(actions_raw),
        "unique_action_canonical": len(actions_canon),
        "top_action_raw": actions_raw.most_common(25),
        "top_action_canonical": actions_canon.most_common(25),
        "category_counts": categories.most_common(),
        "top_unmapped_action_raw": unmapped_actions.most_common(50),
        "rows_per_match_top": Counter(by_match).most_common(20),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="SportsBase CSV -> canonical clip registry (jsonl + summary)")
    ap.add_argument("--sample-dir", required=True)
    ap.add_argument("--out-dir", default="engine/ingest/out")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args()

    sample_dir = Path(args.sample_dir)
    repo_root = Path(args.repo_root)
    out_dir = Path(args.out_dir)

    if not sample_dir.exists():
        raise SystemExit(f"sample-dir not found: {sample_dir}")

    signal_map, alias_map = load_action_mappings(repo_root)

    all_rows: List[ClipRow] = []
    csv_files = list(iter_csv_files(sample_dir))

    for fp in csv_files:
        try:
            all_rows.extend(parse_csv_file(fp, signal_map, alias_map))
        except Exception as e:
            all_rows.append(
                ClipRow(
                    source_file=str(fp.as_posix()),
                    row_id=None,
                    match_id=f"{fp.parent.name}/{fp.stem}",
                    start_s=None,
                    end_s=None,
                    half=None,
                    team_id=None,
                    player_id=None,
                    code_raw="",
                    action_raw=f"__INGEST_ERROR__:{type(e).__name__}",
                    action_canonical="unmapped",
                    action_category="OTHER",
                    pos_x=None,
                    pos_y=None,
                )
            )

    clips_path = out_dir / "clips.jsonl"
    summary_path = out_dir / "clips_summary.json"

    write_jsonl(clips_path, all_rows)
    summary = build_summary(all_rows)
    summary["input_csv_files"] = [str(p.as_posix()) for p in csv_files]
    summary["mapping_signal_mappings_size"] = len(signal_map)
    summary["mapping_tr_action_aliases_size"] = len(alias_map)

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"clips_jsonl": str(clips_path), "summary_json": str(summary_path), "total_rows": len(all_rows)}, ensure_ascii=False))
    return 0 if len(all_rows) > 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())