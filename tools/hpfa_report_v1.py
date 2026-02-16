#!/usr/bin/env python3
import os, sys, json, math
from collections import Counter, defaultdict

# ---- robust keyword sets (TR+EN) ----
KW_SHOT = ("şut", "shot", "vuruş", "kafa vuruş", "volley")
KW_TURNOVER = ("top kayb", "loss", "miscontrol", "bad control", "hata", "turnover")
KW_REGAIN = ("top kazan", "recovery", "interception", "tackle", "ball win", "kapma", "pas arası")
KW_SETPIECE = ("korner", "corner", "freekick", "serbest vuruş", "taç", "throw", "penalt", "penalty")

def s(x): return (x or "").strip().lower()

def load_jsonl(path):
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

def is_kw(text, kws):
    t = s(text)
    return any(k in t for k in kws)

def get_team(rec):
    return rec.get("team_raw") or rec.get("team") or ""

def get_action(rec):
    return rec.get("action") or rec.get("code") or ""

def minute_bucket(t):
    if t is None: return None
    try:
        return int(float(t) // 60)
    except:
        return None

def safe_xy(rec):
    x, y = rec.get("x"), rec.get("y")
    try:
        if x is None or y is None: return None
        x = float(x); y = float(y)
        if math.isnan(x) or math.isnan(y): return None
        return x, y
    except:
        return None

def classify_phase(rec):
    a = get_action(rec)
    c = rec.get("code") or ""
    blob = f"{a} {c}"
    if is_kw(blob, KW_SETPIECE):
        return "F5/F6"
    if is_kw(blob, KW_TURNOVER):
        return "F3"
    if is_kw(blob, KW_REGAIN):
        return "F4"
    # possession phases (F1/F2) need ball-ownership; we mark as "OPEN"
    return "OPEN"

def main():
    if len(sys.argv) != 3:
        print("USAGE: hpfa_report_v1.py <match_out_dir> <report_out_dir>")
        sys.exit(2)

    match_out = sys.argv[1]
    rep_out = sys.argv[2]
    os.makedirs(rep_out, exist_ok=True)

    outfield_path = os.path.join(match_out, "canonical_outfield.jsonl")
    if not os.path.exists(outfield_path):
        print("ERROR: missing", outfield_path)
        sys.exit(1)

    events = load_jsonl(outfield_path)
    if not events:
        print("ERROR: canonical_outfield.jsonl empty/unreadable")
        sys.exit(1)

    # --- metrics ---
    phase_counts = Counter()
    action_counts = Counter()
    per_minute = Counter()
    shots_xy = []
    tov_xy = []

    # prep for regain delta
    # store per-team chronological list
    by_team = defaultdict(list)

    for r in events:
        phase = classify_phase(r)
        phase_counts[phase] += 1

        a = s(r.get("action") or "")
        if a: action_counts[a] += 1

        mb = minute_bucket(r.get("t_start"))
        if mb is not None: per_minute[mb] += 1

        blob = f"{get_action(r)} {r.get('code') or ''}"
        xy = safe_xy(r)
        if xy:
            if is_kw(blob, KW_SHOT): shots_xy.append(xy)
            if is_kw(blob, KW_TURNOVER): tov_xy.append(xy)

        team = get_team(r)
        if team:
            by_team[team].append(r)

    # regain deltas (same team: turnover -> next regain within 30s)
    regain_deltas = []
    for team, lst in by_team.items():
        lst = sorted(lst, key=lambda x: (x.get("t_start") is None, x.get("t_start")))
        # build indices of regain events
        regain_times = []
        for rr in lst:
            blob = f"{get_action(rr)} {rr.get('code') or ''}"
            if is_kw(blob, KW_REGAIN) and rr.get("t_start") is not None:
                try: regain_times.append(float(rr["t_start"]))
                except: pass
        if not regain_times:
            continue
        regain_times.sort()

        for rr in lst:
            blob = f"{get_action(rr)} {rr.get('code') or ''}"
            if not is_kw(blob, KW_TURNOVER): 
                continue
            if rr.get("t_start") is None:
                continue
            try:
                t0 = float(rr["t_start"])
            except:
                continue
            # find first regain time after t0
            t1 = None
            for t in regain_times:
                if t >= t0:
                    t1 = t
                    break
            if t1 is None: 
                continue
            dt = t1 - t0
            if 0 <= dt <= 30:
                regain_deltas.append(dt)

    # ---- write CSV summaries ----
    def write_csv(path, rows, header):
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(header) + "\n")
            for row in rows:
                f.write(",".join(str(x) for x in row) + "\n")

    phase_csv = os.path.join(rep_out, "phase_counts.csv")
    write_csv(phase_csv, sorted(phase_counts.items(), key=lambda x: (-x[1], x[0])), ["phase","count"])

    top_actions_csv = os.path.join(rep_out, "top_actions.csv")
    write_csv(top_actions_csv, action_counts.most_common(30), ["action","count"])

    timeline_csv = os.path.join(rep_out, "events_per_minute.csv")
    rows = [(m, per_minute[m]) for m in sorted(per_minute)]
    write_csv(timeline_csv, rows, ["minute","count"])

    # ---- plots (matplotlib) ----
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print("NO_PLOTS (matplotlib import failed):", e)
        print("CSVs written:", phase_csv, top_actions_csv, timeline_csv)
        sys.exit(0)

    # 1) Phase distribution
    plt.figure()
    labs = [k for k,_ in sorted(phase_counts.items(), key=lambda x: (-x[1], x[0]))]
    vals = [phase_counts[k] for k in labs]
    plt.bar(labs, vals)
    plt.title("Phase buckets (F3/F4/F5F6/OPEN)")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(os.path.join(rep_out, "01_phase_distribution.png"), dpi=160)
    plt.close()

    # 2) Events per minute
    plt.figure()
    mins = sorted(per_minute)
    vals = [per_minute[m] for m in mins]
    plt.plot(mins, vals)
    plt.title("Event intensity (events/min)")
    plt.xlabel("Minute")
    plt.ylabel("Events")
    plt.tight_layout()
    plt.savefig(os.path.join(rep_out, "02_events_per_minute.png"), dpi=160)
    plt.close()

    # 3) Turnover scatter
    plt.figure()
    if tov_xy:
        xs = [x for x,_ in tov_xy]; ys = [y for _,y in tov_xy]
        plt.scatter(xs, ys, s=8)
    plt.title("Turnover locations (proxy)")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.tight_layout()
    plt.savefig(os.path.join(rep_out, "03_turnovers_xy.png"), dpi=160)
    plt.close()

    # 4) Shot scatter
    plt.figure()
    if shots_xy:
        xs = [x for x,_ in shots_xy]; ys = [y for _,y in shots_xy]
        plt.scatter(xs, ys, s=10)
    plt.title("Shot locations (proxy)")
    plt.xlabel("x")
    plt.ylabel("y")
    plt.tight_layout()
    plt.savefig(os.path.join(rep_out, "04_shots_xy.png"), dpi=160)
    plt.close()

    # 5) Regain delta histogram
    plt.figure()
    if regain_deltas:
        plt.hist(regain_deltas, bins=30)
    plt.title("Regain Δt (turnover -> next regain, same team, <=30s)")
    plt.xlabel("seconds")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(os.path.join(rep_out, "05_regain_dt_hist.png"), dpi=160)
    plt.close()

    print("REPORT OK ✅")
    print("OUTDIR:", rep_out)
    print("FILES:")
    for fn in sorted(os.listdir(rep_out)):
        print(" -", fn)

if __name__ == "__main__":
    main()
