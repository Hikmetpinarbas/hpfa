#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP14_BRIEF_V2_RENDER.py
Renders L1/L2/L3 briefs + claims.jsonl with claim->evidence pointers.
NO-GUESSING; includes silence/uncertainty sections.
"""
import argparse, csv, json, os
from datetime import datetime

VERSION = "STEP14_BRIEF_V2_RENDER v0.1"

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def evidence_pointer(file, selector):
    return {"file": file, "selector": selector}

def claim_obj(cid, level, text, evidence, limits, confidence, module):
    return {"id": cid, "level": level, "module": module, "claim": text,
            "evidence": evidence, "limits": limits, "confidence": confidence}

def pick_teams(phase_summary):
    teams = list((phase_summary.get("by_team") or {}).keys())
    teams = [t for t in teams if t != "UNKNOWN_TEAM"] + ([t for t in teams if t == "UNKNOWN_TEAM"])
    return teams

def safe_get(phase_summary, team, phase):
    ph = (((phase_summary.get("by_team") or {}).get(team) or {}).get("phases") or {}).get(phase) or {}
    return ph.get("per_100_events"), ph.get("avg_confidence"), ph.get("count")

def build_silence(module_health, ctx, phase_summary):
    sil = []
    tempo_h = (module_health.get("modules") or {}).get("tempo", {})
    if tempo_h.get("status") in ("OFF","STOP"):
        sil.append({"topic":"tempo", "why": tempo_h.get("reasons", ["unknown"])})
    if phase_summary.get("status") != "OK":
        sil.append({"topic":"phase_tagging_limits", "why": phase_summary.get("reasons", [])})
    if ctx.get("status") != "OK":
        sil.append({"topic":"context", "why": [ctx.get("reason")]})
    return sil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-pack", required=True)
    args = ap.parse_args()

    mp = args.match_pack
    out_dir = os.path.join(mp, "out")
    os.makedirs(out_dir, exist_ok=True)

    ctx = read_json(os.path.join(mp, "context_vector.json"))
    phase_summary = read_json(os.path.join(out_dir, "phase_summary.json"))
    module_health = read_json(os.path.join(out_dir, "module_health.json"))

    teams = pick_teams(phase_summary)
    claims = []
    cid = 1
    L1 = []

    for team in teams[:2]:
        for ph in ("attacking_transition","organized_defense","progression","finalization"):
            rate, avgc, cnt = safe_get(phase_summary, team, ph)
            if rate is None or avgc is None:
                continue
            txt = f"{team}: {ph} = {rate}/100 events (avg_conf={avgc}, n={cnt})."
            evid = [evidence_pointer("out/phase_summary.json", f"by_team['{team}'].phases['{ph}']")]
            conf = float(avgc)
            claims.append(claim_obj(f"C{cid:03d}", "L2", txt, evid, [], min(0.9, conf), "phase_tagger"))
            cid += 1
            if conf >= 0.55 and (cnt or 0) >= 10 and ph in ("attacking_transition","organized_defense"):
                L1.append(f"{team}: {ph} {rate}/100 (conf {avgc}).")

    silence = build_silence(module_health, ctx, phase_summary)
    uncertainty = []
    if phase_summary.get("status") != "OK":
        uncertainty.append({"topic":"phase_tagging", "status": phase_summary.get("status"), "reasons": phase_summary.get("reasons", [])})
    if ctx.get("status") != "OK":
        uncertainty.append({"topic":"context_vector", "status": ctx.get("status"), "reason": ctx.get("reason")})

    if silence:
        L1.append("SILENCE: Bazı başlıklar veri yokluğu/limitleri nedeniyle dışarıda bırakıldı (L2/L3).")
    if not L1:
        L1 = ["SILENCE: TD brif için kanıt yoğunluğu yetersiz veya modüller OFF/DEGRADED."]

    with open(os.path.join(out_dir, "brief_L1.txt"), "w", encoding="utf-8") as f:
        f.write("HP-Motor TD BRIEF (L1)\n")
        f.write(f"generated_at: {now_iso()}\n\n")
        for b in L1[:10]:
            f.write(f"- {b}\n")

    with open(os.path.join(out_dir, "brief_L2.md"), "w", encoding="utf-8") as f:
        f.write("# HP-Motor Maç Brifi (L2)\n\n")
        f.write(f"- generated_at: {now_iso()}\n")
        f.write(f"- engine_version: {VERSION}\n\n")
        f.write("## Claim → Evidence\n\n")
        for c in claims:
            f.write(f"**{c['id']}** ({c['module']}, conf={c['confidence']})  \n")
            f.write(f"- Claim: {c['claim']}\n")
            f.write(f"- Evidence: {json.dumps(c['evidence'], ensure_ascii=False)}\n\n")
        f.write("## Uncertainty\n\n```json\n")
        f.write(json.dumps(uncertainty, ensure_ascii=False, indent=2))
        f.write("\n```\n\n## Silence / Irrelevance\n\n```json\n")
        f.write(json.dumps(silence, ensure_ascii=False, indent=2))
        f.write("\n```\n")

    write_json(os.path.join(out_dir, "brief_L3.json"), {
        "generated_at": now_iso(),
        "engine_version": VERSION,
        "module_health": module_health,
        "context_vector": ctx,
        "phase_summary": phase_summary,
        "silence": silence,
        "uncertainty": uncertainty,
        "claims_count": len(claims),
        "no_guessing": True
    })

    with open(os.path.join(out_dir, "claims.jsonl"), "w", encoding="utf-8") as f:
        for c in claims:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    write_json(os.path.join(out_dir, "template_filled.json"), {
        "match_meta": {"match_id": ctx.get("match_id"), "generated_at": now_iso()},
        "l1": L1,
        "uncertainty": uncertainty,
        "silence": silence,
        "phase_snapshot": phase_summary,
        "no_guessing": True
    })

    print("OK: STEP14 outputs written.")
if __name__ == "__main__":
    main()
