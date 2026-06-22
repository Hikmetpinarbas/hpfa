from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, Iterable, List


def _norm_action(row: Dict[str, Any]) -> str:
    return str(row.get("action") or row.get("event_type") or row.get("code") or "").strip().lower()


def shannon_entropy(items: List[str]) -> float:
    if not items:
        return 0.0
    counts = Counter(items)
    total = float(sum(counts.values()))
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1.0
    return entropy / max_entropy if max_entropy else 0.0


def tempo_cv(rows: List[Dict[str, Any]]) -> float:
    times = []
    for row in rows:
        try:
            times.append(float(row.get("start") or row.get("time_seconds")))
        except Exception:
            pass
    times = sorted(times)
    if len(times) < 3:
        return 0.0
    gaps = [b - a for a, b in zip(times, times[1:]) if b >= a]
    if not gaps:
        return 0.0
    mean = sum(gaps) / len(gaps)
    if mean == 0:
        return 0.0
    variance = sum((g - mean) ** 2 for g in gaps) / len(gaps)
    return math.sqrt(variance) / mean


def zone_power_proxy(rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    attacking = 0
    valid = 0
    for row in rows:
        try:
            x = float(row.get("pos_x"))
        except Exception:
            continue
        valid += 1
        if x >= 70.0:
            attacking += 1
    return attacking / valid if valid else 0.0


def build_signal_profile(rows: Iterable[Dict[str, Any]], *, team: str = "") -> Dict[str, Any]:
    selected = [dict(r) for r in rows if not team or team in str(r.get("team") or r.get("team_id") or "")]
    actions = [_norm_action(r) for r in selected]
    entropy = shannon_entropy(actions)
    cv = tempo_cv(selected)
    zone_power = zone_power_proxy(selected)

    low_value_loop_fraction = 0.0
    if selected:
        low_value = 0
        for row in selected:
            action = _norm_action(row)
            try:
                x = float(row.get("pos_x"))
            except Exception:
                x = 0.0
            if x < 70.0 and ("pass" in action or "passes" in action):
                low_value += 1
        low_value_loop_fraction = low_value / len(selected)

    sterile = entropy <= 0.35 and zone_power <= 0.10 and low_value_loop_fraction >= 0.60
    chaos = cv >= 1.50 and zone_power <= 0.10

    return {
        "surface_row_count": len(selected),
        "raw_entropy": round(entropy, 6),
        "tempo_cv": round(cv, 6),
        "zone_power_proxy": round(zone_power, 6),
        "low_value_loop_fraction": round(low_value_loop_fraction, 6),
        "sterile_circulation_candidate": bool(sterile),
        "chaos_noise_candidate": bool(chaos),
        "claim_safety": "EVIDENCE_ONLY",
        "method_note": "Entropy is computed on raw action strings. Median/Savitzky-Golay/STFT are not used for claim-driving inference in V1."
    }
