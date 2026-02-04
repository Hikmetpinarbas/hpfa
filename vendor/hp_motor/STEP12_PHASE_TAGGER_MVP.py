#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP12_PHASE_TAGGER_MVP.py
Event-only 6-phase tagger with NO-GUESSING + OK/DEGRADED/OFF health.
Outputs: out/phase_timeline.csv, out/phase_summary.json, out/module_health.json
"""
import argparse, csv, json, os, sys
from collections import defaultdict, Counter

VERSION = "STEP12_PHASE_TAGGER_MVP v0.1"

CANON = [
    "match_id","event_id","team","opponent","period","t_game_sec","minute","second",
    "event_type","outcome","x","y","end_x","end_y","zone","end_zone"
]

DEFAULT_EVENT_SETS = {
    "ON_BALL": {"pass","carry","dribble","shot","cross","goal_kick","free_kick","corner","throw_in"},
    "REGAIN": {"ball_recovery","interception","tackle_won","keeper_save","claim","pickup","foul_won"},
    "TURNOVER": {"dispossessed","miscontrol","ball_lost","tackle_lost","interception_against","foul_committed"},
    "DEF_ACTION": {"pressure","tackle","interception","foul_committed","block","clearance","duel"}
}

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def ensure_out_dir(match_pack):
    out_dir = os.path.join(match_pack, "out")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

def load_alias_map(match_pack, alias_path=None):
    if alias_path:
        return read_json(alias_path)
    candidate = os.path.join(match_pack, "alias_map.json")
    if os.path.exists(candidate):
        return read_json(candidate)
    return {}

def canonicalize_header(fieldnames, alias_map):
    found = {}
    lower_to_actual = {c.lower(): c for c in fieldnames}
    for c in CANON:
        if c in fieldnames:
            found[c] = c
            continue
        if c.lower() in lower_to_actual:
            found[c] = lower_to_actual[c.lower()]
            continue
        aliases = alias_map.get(c, [])
        hit = None
        for a in aliases:
            if a in fieldnames:
                hit = a; break
            if a.lower() in lower_to_actual:
                hit = lower_to_actual[a.lower()]; break
        if hit:
            found[c] = hit
    return found

def coerce_float(v):
    if v is None: return None
    s = str(v).strip()
    if s == "" or s.lower() in ("na","nan","none","null"):
        return None
    try:
        return float(s)
    except:
        return None

def coerce_int(v):
    if v is None: return None
    s = str(v).strip()
    if s == "" or s.lower() in ("na","nan","none","null"):
        return None
    try:
        return int(float(s))
    except:
        return None

def get_first_present(row, mapping, key):
    col = mapping.get(key)
    if not col:
        return None
    return row.get(col)

def normalize_event_type(s):
    if s is None: return None
    t = str(s).strip().lower()
    if t == "": return None
    t = t.replace(" ", "_").replace("-", "_")
    return t

def load_events(events_csv_path, mapping):
    events = []
    with open(events_csv_path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            ev = {
                "seq_idx": i,
                "match_id": get_first_present(row, mapping, "match_id"),
                "event_id": get_first_present(row, mapping, "event_id"),
                "team": get_first_present(row, mapping, "team"),
                "opponent": get_first_present(row, mapping, "opponent"),
                "period": coerce_int(get_first_present(row, mapping, "period")),
                "t_game_sec": coerce_float(get_first_present(row, mapping, "t_game_sec")),
                "minute": coerce_int(get_first_present(row, mapping, "minute")),
                "second": coerce_int(get_first_present(row, mapping, "second")),
                "event_type": normalize_event_type(get_first_present(row, mapping, "event_type")),
                "outcome": (get_first_present(row, mapping, "outcome") or "").strip().lower() or None,
                "x": coerce_float(get_first_present(row, mapping, "x")),
                "y": coerce_float(get_first_present(row, mapping, "y")),
                "end_x": coerce_float(get_first_present(row, mapping, "end_x")),
                "end_y": coerce_float(get_first_present(row, mapping, "end_y")),
                "zone": (get_first_present(row, mapping, "zone") or "").strip().lower() or None,
                "end_zone": (get_first_present(row, mapping, "end_zone") or "").strip().lower() or None,
            }
            events.append(ev)
    return events

def module_health(status, reasons, required_cols, provided_cols):
    return {"status": status, "reasons": reasons, "required_cols": required_cols, "provided_cols": provided_cols}

def ensure_context_vector(match_pack, events):
    ctx_path = os.path.join(match_pack, "context_vector.json")
    if os.path.exists(ctx_path):
        return ctx_path, "OK", []
    match_ids = [e["match_id"] for e in events if e["match_id"] not in (None,"")]
    match_id = match_ids[0] if match_ids else None
    stub = {
        "status": "DEGRADED",
        "reason": "context_vector.json missing; stub created with nulls (NO-GUESSING).",
        "match_id": match_id,
        "verified": {"score_state": False,"minute_bin": False,"home_away": False,"red_card": False,"competition_stage": False},
        "fields": {"score_state": None,"minute_bin": None,"home_away": None,"red_card": None,"late_goal": None,"fatigue_window": None,"opponent_profile_soft": None}
    }
    write_json(ctx_path, stub)
    return ctx_path, "DEGRADED", ["context_vector.json yoktu; stub üretildi."]

def infer_possession_team(events, sets):
    poss = []
    cur = None
    pending_regain = None
    for i, e in enumerate(events):
        et = e["event_type"]
        team = e["team"]
        evidence = []
        confidence = 0.0
        if team and et in sets["ON_BALL"]:
            cur = team
            evidence.append("poss:on_ball_team")
            confidence = 0.85
            pending_regain = None
        elif team and et in sets["REGAIN"]:
            pending_regain = (team, i)
            evidence.append("poss:regain_pending")
            confidence = 0.55
        else:
            if pending_regain and team and et in sets["ON_BALL"] and team == pending_regain[0]:
                cur = team
                evidence.append("poss:regain_confirmed_next_on_ball")
                confidence = 0.70
                pending_regain = None
            else:
                evidence.append("poss:carry_forward_or_unknown")
                confidence = 0.40 if cur else 0.10
        poss.append({"possession_team": cur, "poss_conf": confidence, "poss_evidence": ";".join(evidence)})
    return poss

def zone_bucket(x):
    if x is None: return None
    if x < 0 or x > 120: return None
    if x <= 100:
        if x < 33.33: return "own_third"
        if x < 66.66: return "mid_third"
        return "att_third"
    else:
        if x < 40: return "own_third"
        if x < 80: return "mid_third"
        return "att_third"

def progressive_proxy(e):
    x, ex = e["x"], e["end_x"]
    if x is not None and ex is not None:
        dx = ex - x
        thresh = 10.0 if ex <= 100 else 12.0
        return dx >= thresh, f"dx={dx:.1f}>=thresh"
    return None, "no_xy"

def classify_phase(events, poss_info, sets, N_trans=6):
    phase_rows = []
    last_poss = None
    last_regain_i = None
    last_loss_i = None
    for i, e in enumerate(events):
        poss_team = poss_info[i]["possession_team"]
        et = e["event_type"]
        team = e["team"]
        conf = 0.0
        tags = []
        limits = []
        if poss_team is not None and poss_team != last_poss:
            if last_poss is not None: last_loss_i = i
            last_regain_i = i
            last_poss = poss_team
        in_poss = (team is not None and poss_team is not None and team == poss_team)
        if poss_team is None: limits.append("possession_unknown")
        if e["x"] is None or e["end_x"] is None: limits.append("no_xy")
        if e["t_game_sec"] is None and (e["minute"] is None or e["second"] is None): limits.append("no_time")
        phase = "UNKNOWN"
        if in_poss:
            if last_regain_i is not None and (i - last_regain_i) <= N_trans:
                prog, why = progressive_proxy(e)
                if et == "shot" or prog is True:
                    phase = "attacking_transition"; conf = 0.65 if prog is True else 0.55
                    tags += ["phase:att_trans", f"prog:{why}", "window:regain"]
                else:
                    phase = "attacking_transition"; conf = 0.45
                    tags += ["phase:att_trans_low", "window:regain", f"prog:{why}"]
            if not phase.startswith("attacking_transition"):
                if et == "shot":
                    phase = "finalization"; conf = 0.85; tags += ["phase:finalization","shot"]
                else:
                    z = zone_bucket(e["x"]) or e["zone"]
                    ez = zone_bucket(e["end_x"]) or e["end_zone"]
                    if ez in ("att_third","box") and (et in ("pass","carry","dribble","cross")):
                        phase = "progression" if (z in ("own_third","mid_third") and ez in ("att_third","box")) else "finalization"
                        conf = 0.60 if ez == "att_third" else 0.55
                        tags += [f"z:{z}", f"ez:{ez}", "entry_proxy"]
                    else:
                        z = zone_bucket(e["x"]) or e["zone"]
                        if z == "own_third" and et in ("pass","goal_kick","free_kick","throw_in"):
                            phase = "build_up"; conf = 0.55 if e["x"] is not None else 0.40
                            tags += ["phase:build_up", f"z:{z}"]
                        else:
                            prog, why = progressive_proxy(e)
                            if prog is True:
                                phase = "progression"; conf = 0.70; tags += ["phase:progression", f"prog:{why}"]
                            else:
                                phase = "progression"; conf = 0.35; tags += ["phase:progression_low", f"prog:{why}"]
        else:
            if last_loss_i is not None and team is not None and (i - last_loss_i) <= N_trans and (et in sets["DEF_ACTION"]):
                phase = "defensive_transition"; conf = 0.55
                tags += ["phase:def_trans","window:loss",f"def_action:{et}"]
            else:
                phase = "organized_defense"; conf = 0.45 if team is not None else 0.20
                tags += ["phase:org_def"]
        if "possession_unknown" in limits:
            conf = min(conf, 0.25); tags.append("cap:possession_unknown")
        if "no_xy" in limits and phase in ("build_up","progression","finalization"):
            conf = min(conf, 0.55); tags.append("cap:no_xy")
        conf = round(float(conf), 3)
        phase_rows.append({
            "seq_idx": e["seq_idx"], "match_id": e["match_id"] or "", "event_id": e["event_id"] or "",
            "period": e["period"] if e["period"] is not None else "",
            "t_game_sec": e["t_game_sec"] if e["t_game_sec"] is not None else "",
            "minute": e["minute"] if e["minute"] is not None else "",
            "second": e["second"] if e["second"] is not None else "",
            "team": e["team"] or "", "event_type": e["event_type"] or "", "possession_team": poss_team or "",
            "phase": phase, "phase_confidence": conf,
            "evidence_tags": ";".join(tags), "limits": ";".join(sorted(set(limits))),
            "poss_confidence": poss_info[i]["poss_conf"], "poss_evidence": poss_info[i]["poss_evidence"]
        })
    return phase_rows

def summarize_phases(phase_rows):
    per_team = defaultdict(lambda: Counter())
    conf_sum = defaultdict(lambda: defaultdict(float))
    conf_n = defaultdict(lambda: defaultdict(int))
    for r in phase_rows:
        team = r["team"] or "UNKNOWN_TEAM"
        ph = r["phase"]
        per_team[team][ph] += 1
        conf_sum[team][ph] += float(r["phase_confidence"])
        conf_n[team][ph] += 1
    summary = {"by_team": {}}
    for team, cnt in per_team.items():
        total = sum(cnt.values()) or 1
        phases = {}
        for ph, c in cnt.items():
            avg = conf_sum[team][ph] / max(1, conf_n[team][ph])
            phases[ph] = {"count": int(c), "per_100_events": round(100.0*c/total, 2), "avg_confidence": round(avg, 3)}
        summary["by_team"][team] = {"total_events": total, "phases": phases}
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-pack", required=True)
    ap.add_argument("--events", default="events.csv")
    ap.add_argument("--alias", default=None)
    ap.add_argument("--n-trans", type=int, default=6)
    args = ap.parse_args()
    mp = args.match_pack
    out_dir = ensure_out_dir(mp)
    events_path = os.path.join(mp, args.events)
    if not os.path.exists(events_path):
        print(f"STOP: events.csv not found: {events_path}"); sys.exit(2)
    alias_map = load_alias_map(mp, args.alias)
    with open(events_path, "r", encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    mapping = canonicalize_header(header, alias_map)
    provided = sorted(list(mapping.keys()))
    required = ["team","event_type"]
    missing = [c for c in required if c not in mapping]
    health = {"version": VERSION, "modules": {}}
    if missing:
        health["modules"]["phase_tagger"] = module_health("OFF", [f"missing required columns: {missing}"], required, provided)
        write_json(os.path.join(out_dir, "module_health.json"), health)
        print("OFF: phase_tagger (missing required columns)."); sys.exit(0)
    events = load_events(events_path, mapping)
    _, ctx_status, ctx_reasons = ensure_context_vector(mp, events)
    health["modules"]["context_vector"] = module_health(ctx_status, ctx_reasons, ["context_vector.json"], ["context_vector.json"])
    has_xy = ("x" in mapping and "end_x" in mapping)
    has_time = ("t_game_sec" in mapping) or ("minute" in mapping and "second" in mapping)
    status = "OK"; reasons=[]
    if not has_xy: status="DEGRADED"; reasons.append("no_xy: territory/progression proxies limited")
    if not has_time: status="DEGRADED"; reasons.append("no_time: per-minute rates unavailable, event-based only")
    poss_info = infer_possession_team(events, DEFAULT_EVENT_SETS)
    phase_rows = classify_phase(events, poss_info, DEFAULT_EVENT_SETS, N_trans=args.n_trans)
    out_csv = os.path.join(out_dir, "phase_timeline.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(phase_rows[0].keys()))
        w.writeheader()
        for r in phase_rows: w.writerow(r)
    summary = summarize_phases(phase_rows)
    summary["status"] = status
    summary["reasons"] = reasons
    summary["notes"] = {"denominator":"per_100_events","no_guessing":True,"transition_window_events":args.n_trans}
    write_json(os.path.join(out_dir, "phase_summary.json"), summary)
    health["modules"]["phase_tagger"] = module_health(status, reasons, required, provided)
    write_json(os.path.join(out_dir, "module_health.json"), health)
    print("OK: STEP12 outputs written.")
if __name__ == "__main__":
    main()
