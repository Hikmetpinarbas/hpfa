import json, os, sys
from pathlib import Path
from collections import Counter

ACTIONS = ["PASS", "WARN", "QUARANTINE"]

def die(msg: str, code: int = 2):
    print(msg)
    raise SystemExit(code)

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"[FAIL] cannot read json: {p} :: {e}")

def main():
    out_dir = os.environ.get("OUT_DIR")
    if not out_dir:
        die("[FAIL] OUT_DIR is not set. export OUT_DIR=/path/to/engine_run_xxx")
    out = Path(out_dir)

    stamped_p = out / "engine_meta_stamped.json"
    seq_p = out / "engine_seq_possessions.json"
    xt_p = out / "engine_xt01_grid.json"

    for p in [stamped_p, seq_p, xt_p]:
        if not p.exists():
            die(f"[FAIL] missing artifact: {p}")

    stamped = load_json(stamped_p)
    seq = load_json(seq_p)
    xt = load_json(xt_p)

    findings = []
    action = "PASS"

    # --- Evidence presence ---
    inp = stamped.get("input", {})
    if not inp.get("source_csv_sha256"):
        findings.append({"rule": "evidence.input_hash", "status": "FAIL", "detail": "missing input.source_csv_sha256"})
        action = "QUARANTINE"

    ev = stamped.get("evidence", {})
    ah = (ev.get("artifact_sha256") or {})
    for k in ["engine_meta.json", "engine_seq_possessions.json", "engine_xt01_grid.json"]:
        if not ah.get(k.replace(".json", ".json")) and not ah.get(k):
            findings.append({"rule": "evidence.artifact_hash", "status": "FAIL", "detail": f"missing sha256 for {k}"})
            action = "QUARANTINE"

    # --- Seq format ---
    for k in ["policy", "n_possessions", "summaries"]:
        if k not in seq:
            findings.append({"rule": "seq.required_keys", "status": "FAIL", "detail": f"missing {k}"})
            action = "QUARANTINE"

    summ = seq.get("summaries")
    if not isinstance(summ, list) or (len(summ) == 0):
        findings.append({"rule": "seq.summaries_list", "status": "FAIL", "detail": "summaries must be non-empty list"})
        action = "QUARANTINE"
    else:
        need_keys = ["possession_id","team","half","t_start","t_end","n_events","start_xy","end_xy"]
        miss = [k for k in need_keys if k not in (summ[0] or {})]
        if miss:
            findings.append({"rule": "seq.summaries_schema", "status": "FAIL", "detail": f"missing keys in summaries[0]: {miss}"})
            action = "QUARANTINE"

    # --- XT format + degeneracy check ---
    for k in ["grid_spec", "solve_spec", "grid_values"]:
        if k not in xt:
            findings.append({"rule": "xt.required_keys", "status": "FAIL", "detail": f"missing {k}"})
            action = "QUARANTINE"

    gv = xt.get("grid_values") or {}
    if not isinstance(gv, dict) or len(gv) == 0:
        findings.append({"rule": "xt.grid_values", "status": "FAIL", "detail": "grid_values must be non-empty dict"})
        action = "QUARANTINE"
    else:
        # degeneracy: all zeros
        vals = list(gv.values())
        if all((v == 0 or v == 0.0) for v in vals):
            findings.append({"rule": "xt.degenerate_all_zero", "status": "WARN", "detail": "all grid values are 0. likely missing x/y in input"})
            if action != "QUARANTINE":
                action = "WARN"

    # --- coord presence from raw meta ---
    raw = stamped.get("raw_engine_meta") or {}
    seen_xy = (((raw.get("modules") or {}).get("coord_normalize") or {}).get("seen_xy"))
    if seen_xy in (0, 0.0, None):
        findings.append({"rule": "coord.seen_xy", "status": "WARN", "detail": f"seen_xy={seen_xy}. spatial features absent"})
        if action != "QUARANTINE":
            action = "WARN"

    # --- team quality: UNKNOWN share ---
    teams = []
    if isinstance(summ, list):
        for it in summ:
            t = (it or {}).get("team")
            if t is not None:
                teams.append(str(t))
    if teams:
        c = Counter(teams)
        unk = c.get("UNKNOWN", 0) + c.get("unknown", 0)
        ratio = unk / max(1, len(teams))
        if ratio > 0.25:
            findings.append({"rule": "team.unknown_ratio", "status": "WARN", "detail": f"UNKNOWN ratio in summaries: {ratio:.2%}"})
            if action != "QUARANTINE":
                action = "WARN"

    report = {
        "action": action,
        "out_dir": out.as_posix(),
        "engine_id": stamped.get("engine_id"),
        "provider": stamped.get("provider"),
        "algo_version": stamped.get("algo_version"),
        "findings": findings
    }

    out_p = out / "engine_gate_report.json"
    out_p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[OK] action:", action)
    print("[OK] wrote:", out_p.as_posix())

if __name__ == "__main__":
    main()
