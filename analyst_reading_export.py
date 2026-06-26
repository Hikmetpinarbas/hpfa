from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

OUTPUT_JSON = "analyst_reading_export_lite_v1.json"
OUTPUT_TXT = "analyst_reading_export_lite_v1.txt"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def n(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def f(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def add(counter: Counter[str], value: Any) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            counter[str(k)] += n(v)


def rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("event_windows")
    if not isinstance(data, list):
        data = payload.get("event_windows_sample")
    return [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []


def top(counter: Counter[str], limit: int = 6) -> list[tuple[str, int, float]]:
    total = sum(counter.values())
    return [(k, v, round((v / total) * 100, 1) if total else 0.0) for k, v in counter.most_common(limit)]


def module_path(repo_root: Path) -> None:
    p = repo_root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def validate_out(repo_root: Path, out_dir: Path) -> Path:
    module_path(repo_root)
    import spine_runner  # type: ignore
    return spine_runner.validate_output_root(out_dir)


def build(input_dir: Path) -> dict[str, Any]:
    full = read_json(input_dir / "active_match_full_run_lite_v1.json")
    ewb = read_json(input_dir / "event_window_builder_lite_v1.json")
    tsr = read_json(input_dir / "time_scale_router_lite_v1.json")
    axis = read_json(input_dir / "axis_integrity_tagger_lite_v1.json")
    win = rows(ewb)
    actions: Counter[str] = Counter()
    zones: Counter[str] = Counter()
    channels: Counter[str] = Counter()
    teams: Counter[str] = Counter()
    for w in win:
        add(actions, w.get("action_family_counts"))
        add(zones, w.get("zone_counts"))
        add(channels, w.get("channel_counts"))
        add(teams, w.get("team_label_counts"))
    dense = sorted(win, key=lambda x: f(x.get("context_density")), reverse=True)[:6]
    terminal = [w for w in win if bool(w.get("terminal_action_surface_present"))][:6]
    restart = [w for w in win if bool(w.get("restart_surface_present"))][:6]
    return {
        "module_id": "analyst_reading_export_lite_v1",
        "status": "REVIEW_REQUIRED",
        "decision": "ANALYST_READING_EXPORTED",
        "claim_safety": "ANALYST_READING_CANDIDATE_ONLY",
        "runtime": {
            "input_context_count": ewb.get("input_context_count"),
            "minute_bearing_context_count": ewb.get("minute_bearing_context_count"),
            "event_window_count": ewb.get("event_window_count"),
            "routed_window_count": tsr.get("routed_window_count"),
            "minute_axis_window_count": tsr.get("minute_axis_window_count"),
            "axis_integrity_score": axis.get("axis_integrity_score"),
            "full_run_valid": full.get("engineering_evidence", {}).get("valid_run"),
        },
        "axis_status": axis.get("axis_status", {}),
        "downstream_permissions": axis.get("downstream_permissions", {}),
        "surface": {
            "actions": top(actions, 8),
            "zones": top(zones, 6),
            "channels": top(channels, 6),
            "teams": top(teams, 6),
        },
        "windows": {
            "high_density": [window_card(w) for w in dense],
            "terminal_surface": [window_card(w) for w in terminal],
            "restart_surface": [window_card(w) for w in restart],
        },
        "claim_boundary": {
            "canonical_event_count": "UNKNOWN",
            "phase_truth": False,
            "possession_truth": False,
            "sequence_truth": False,
            "rhythm_truth": False,
            "tactical_truth": False,
            "dominance_truth": False,
        },
    }


def window_card(w: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": w.get("window_id"),
        "minutes": f"{w.get('start_minute')}-{w.get('end_minute')}",
        "rows": w.get("surface_row_count"),
        "density": w.get("context_density"),
        "confidence": w.get("window_confidence"),
        "actions": top(Counter({str(k): n(v) for k, v in w.get("action_family_counts", {}).items()}), 4),
        "zones": top(Counter({str(k): n(v) for k, v in w.get("zone_counts", {}).items()}), 4),
        "teams": top(Counter({str(k): n(v) for k, v in w.get("team_label_counts", {}).items()}), 4),
    }


def render(report: dict[str, Any]) -> str:
    r = report.get("runtime", {})
    lines = [
        "HPFA ANALYST READING EXPORT LITE V1",
        "====================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        "",
        "1) MACIN OKUNABILIRLIK DURUMU",
        f"- Sistem {r.get('input_context_count')} context adayini okudu; {r.get('minute_bearing_context_count')} adayi zaman bilgisi tasiyor.",
        f"- Mac {r.get('event_window_count')} dakika penceresine bolundu; {r.get('routed_window_count')} pencere route edildi.",
        f"- Minute-axis pencere sayisi {r.get('minute_axis_window_count')}; axis integrity skoru {r.get('axis_integrity_score')}.",
        "- Bu, profesyonel okuma icin zemin oldugunu gosterir; fakat kesin faz, sekans veya taktik dogrusu uretmez.",
        "",
        "2) ANALIZ EKSENLERI",
    ]
    for k, v in report.get("axis_status", {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("3) SAHA UZERINDE GORULEN YUZEYLER")
    for title, key in [("Aksiyon aileleri", "actions"), ("Bolgeler", "zones"), ("Kanallar", "channels"), ("Takim satir hacmi", "teams")]:
        lines.append(f"[{title}]")
        for label, count, pct in report.get("surface", {}).get(key, []):
            lines.append(f"- {label}: {count} surface rows ({pct}%)")
    lines.append("")
    lines.append("4) OYUN AKISI ADAY OKUMASI")
    lines.append("- Yuksek yogunluklu pencereler macin ritim adaylarini isaret eder; bunlar rhythm truth degildir.")
    lines.append("- Terminal surface pencereleri sut/final aksiyon yuzeyi bulunan zaman araliklarini isaret eder; bu chance quality degildir.")
    lines.append("- Restart surface pencereleri duran top veya tekrar baslama sinyali tasiyan araliklari isaret eder.")
    for group, items in report.get("windows", {}).items():
        lines.append(f"[{group}]")
        for item in items:
            lines.append(f"- {item.get('minutes')} | rows={item.get('rows')} | density={item.get('density')} | confidence={item.get('confidence')}")
            lines.append(f"  actions={item.get('actions')}")
            lines.append(f"  zones={item.get('zones')}")
            lines.append(f"  teams={item.get('teams')}")
    lines.append("")
    lines.append("5) TEKNIK DIREKTOR ICIN KISA SONUC")
    lines.append("- Bu cikti macin hangi zaman pencerelerinde yogunlastigini, hangi aksiyon ailelerinin one ciktigini ve hangi saha bolgelerinin daha fazla gorundugunu aday olarak gosterir.")
    lines.append("- Bir sonraki urun katmani phase candidate, sequence candidate ve pattern candidate uretmelidir.")
    lines.append("- Mevcut rapor guvenli okuma raporudur; kesin taktik niyet, dominasyon veya possession truth iddiasi kurmaz.")
    lines.append("")
    lines.append("CLAIM BOUNDARY")
    for k, v in report.get("claim_boundary", {}).items():
        lines.append(f"- {k}={v}")
    return "\n".join(lines) + "\n"


def write(input_dir: Path, out_dir: Path, repo_root: Path) -> dict[str, Any]:
    out = validate_out(repo_root, out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build(input_dir)
    report["outputs"] = {"json": str(out / OUTPUT_JSON), "txt": str(out / OUTPUT_TXT)}
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (out / OUTPUT_TXT).write_text(render(report), encoding="utf-8")
    return report


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="runtime/outputs/active_match_current")
    parser.add_argument("--out-dir", default="runtime/outputs/active_match_current")
    args = parser.parse_args()
    inp = Path(args.input_dir)
    out = Path(args.out_dir)
    if not inp.is_absolute():
        inp = repo_root / inp
    if not out.is_absolute():
        out = repo_root / out
    report = write(inp, out, repo_root)
    print(json.dumps({"status": report.get("status"), "decision": report.get("decision"), "outputs": report.get("outputs"), "runtime": report.get("runtime")}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
