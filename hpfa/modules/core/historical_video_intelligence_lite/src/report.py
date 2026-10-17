"""Validation summary + measurement report (JSON and Markdown)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation import admit_capability
from hvi_contract import EVENT_TYPES, wilson_interval


def pool(reports: list[dict[str, Any]]) -> dict[str, Any]:
    pooled: dict[str, Any] = {}
    hours = sum(r["measurement"]["video_duration_s"] for r in reports) / 3600.0
    for et in EVENT_TYPES:
        rows = [r["evaluation"]["per_event_type"][et] for r in reports if r.get("evaluation") and et in r["evaluation"]["per_event_type"]]
        if not rows:
            continue
        tp = sum(x["true_positive"] for x in rows)
        c = sum(x["candidates"] for x in rows)
        n = sum(x["references"] for x in rows)
        fp = sum(x["false_positive"] for x in rows)
        audit_n = sum(x["random_audit_reference_n"] for x in rows)
        audit_hit = sum(round((x["triage_window_recall_random_audit_estimate"] or 0) * x["random_audit_reference_n"]) for x in rows)
        triage_true = sum(round((x["triage_window_recall_true"] or 0) * x["references"]) for x in rows)
        p_ci, r_ci = wilson_interval(tp, c), wilson_interval(tp, n)
        pooled[et] = {
            "tolerance_s": rows[0]["tolerance_s"],
            "candidates": c,
            "references": n,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": n - tp,
            "precision": round(tp / c, 4) if c else None,
            "precision_wilson95": [round(v, 4) for v in p_ci] if p_ci else None,
            "recall": round(tp / n, 4) if n else None,
            "recall_wilson95": [round(v, 4) for v in r_ci] if r_ci else None,
            "f1": round(2 * tp / (c + n), 4) if (c + n) else None,
            "false_positive_per_video_hour": round(fp / hours, 3) if hours else None,
            "triage_window_recall_true": round(triage_true / n, 4) if n else None,
            "triage_window_recall_random_audit_estimate": round(audit_hit / audit_n, 4) if audit_n else None,
            "random_audit_reference_n": audit_n,
            "construct_match": sorted({m for x in rows for m in x.get("construct_match", [])}),
        }
    return pooled


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt(x) for x in v) + "]"
    return str(v)


def measurement_rows(r: dict[str, Any]) -> dict[str, Any]:
    m = r["measurement"]
    a, b = m["stage_a"], m["stage_b"]
    return {
        "video": r.get("video", {}).get("source_video_id"),
        "role": r.get("role"),
        "duration_s": m["video_duration_s"],
        "resolution": "x".join(str(x) for x in m["video_resolution"]),
        "native_fps": m["video_native_fps"],
        "a_signal": a["mode"],
        "a_rate_hz": a["effective_sample_rate_hz"],
        "a_wall_s": a["resources"]["wall_s"],
        "a_rtf": a["realtime_factor"],
        "triage_cov": a["triage_coverage_fraction"],
        "audit_cov": a["random_audit_coverage_fraction"],
        "b_fps": b["fps"],
        "b_width": b["analysis_width_px"],
        "b_cov": b["coverage_fraction"],
        "b_frames": b["frames"],
        "b_wall_s": b["resources"]["wall_s"],
        "cpu_s": round(a["resources"]["cpu_python_s"] + a["resources"]["cpu_ffmpeg_children_s"] + b["resources"]["cpu_python_s"] + b["resources"]["cpu_ffmpeg_children_s"], 1),
        "peak_rss_mb": max(a["resources"]["peak_rss_python_mb"], b["resources"]["peak_rss_python_mb"]),
        "ffmpeg_rss_mb": max(a["resources"]["peak_rss_ffmpeg_child_max_mb"], b["resources"]["peak_rss_ffmpeg_child_max_mb"]),
        "total_wall_s": m["total_wall_s"],
        "total_rtf": m["total_realtime_factor"],
        "host": m["host"],
    }


def write_report(out: Path, reports: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    held = reports["heldout"]
    pooled = pool(held)
    capability = admit_capability(pooled)
    domain = held[0]["video"]["footage_domain"] if held else None
    summary = {
        "report_id": "historical_video_intelligence_validation_v1",
        "status": "VALIDATION_EVIDENCE_HELDOUT" if held else "NO_HELDOUT_EVIDENCE",
        "dataset_attribution": manifest.get("attribution"),
        "license": manifest.get("license"),
        "footage_domain": domain,
        "calibration_video": reports["calibration"].get("video", {}).get("source_video_id"),
        "calibration_params": (reports["calibration"].get("calibration") or {}).get("best_params"),
        "heldout_videos": [r["video"]["source_video_id"] for r in held],
        "heldout_pooled": pooled,
        "heldout_per_video": {r["video"]["source_video_id"]: r["evaluation"]["per_event_type"] for r in held},
        "calibration_in_sample": reports["calibration"]["evaluation"]["per_event_type"],
        "capability_admission_heldout": {"validated_domain": domain, "capability": capability},
        "measurement": [measurement_rows(reports["calibration"])] + [measurement_rows(r) for r in held],
        "claim_boundary": {
            "domain_transfer_admitted": False,
            "historical_broadcast_footage_validated": False,
            "detector_score_is_probability": False,
            "tracking_statistics_emitted": False,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        },
    }
    (out / "validation_summary_v1.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (out / "capability_heldout_v1.json").write_text(json.dumps(summary["capability_admission_heldout"], indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# HPFA Historical Video Intelligence — Validation & Measurement Report V1",
        "",
        f"- Dataset: {manifest.get('attribution')}",
        f"- Licence: {manifest.get('license')} ({manifest.get('license_url')})",
        f"- Footage domain: `{domain}`",
        f"- Calibration (in-sample, threshold search on Stage B only): `{summary['calibration_video']}` → {summary['calibration_params']}",
        f"- Held-out test videos: {', '.join('`' + v + '`' for v in summary['heldout_videos'])}",
        "",
        "## Held-out event capture (pooled)",
        "",
        "| Event | Tol. s | Refs | Cands | TP | FP | Precision [95% CI] | Recall [95% CI] | FP / video-h | Triage recall (true) | Triage recall (random-audit est., n) | Construct match |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for et, m in pooled.items():
        lines.append(
            f"| {et} | {_fmt(m['tolerance_s'])} | {m['references']} | {m['candidates']} | {m['true_positive']} | {m['false_positive']} | "
            f"{_fmt(m['precision'])} {_fmt(m['precision_wilson95'])} | {_fmt(m['recall'])} {_fmt(m['recall_wilson95'])} | {_fmt(m['false_positive_per_video_hour'])} | "
            f"{_fmt(m['triage_window_recall_true'])} | {_fmt(m['triage_window_recall_random_audit_estimate'])} (n={m['random_audit_reference_n']}) | {', '.join(m['construct_match'])} |"
        )
    lines += ["", "## Capability admission from held-out evidence", "", "| Event | Status | Reason |", "|---|---|---|"]
    for et, c in capability.items():
        lines.append(f"| {et} | `{c['status']}` | {c['reason']} |")
    lines += [
        "",
        "## Measurement (sampling, coverage, time, resources)",
        "",
        "| Video | Role | Dur. s | Res. | Stage A signal | A rate Hz | A wall s | A RTF | Triage cov. | Audit cov. | B fps | B width | B cov. | B frames | B wall s | CPU s | Py RSS MB | ffmpeg RSS MB | Total wall s | Total RTF |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in summary["measurement"]:
        lines.append(
            f"| {r['video']} | {r['role']} | {_fmt(r['duration_s'])} | {r['resolution']} | {r['a_signal']} | {_fmt(r['a_rate_hz'])} | {_fmt(r['a_wall_s'])} | {_fmt(r['a_rtf'])} | "
            f"{_fmt(r['triage_cov'])} | {_fmt(r['audit_cov'])} | {_fmt(r['b_fps'])} | {r['b_width']} | {_fmt(r['b_cov'])} | {r['b_frames']} | {_fmt(r['b_wall_s'])} | "
            f"{_fmt(r['cpu_s'])} | {_fmt(r['peak_rss_mb'])} | {_fmt(r['ffmpeg_rss_mb'])} | {_fmt(r['total_wall_s'])} | {_fmt(r['total_rtf'])} |"
        )
    host = summary["measurement"][0]["host"] if summary["measurement"] else {}
    lines += [
        "",
        f"Host: {host.get('platform')} · CPUs {host.get('cpu_count')} · GPU {host.get('gpu')} · Colab {host.get('colab')}",
        "",
        "## Claim boundary",
        "",
        "- Detector scores are uncalibrated ranks, not probabilities. Confidence bounds above are Wilson 95% intervals of held-out precision/recall.",
        "- `SUPPORTED_IN_VALIDATED_DOMAIN` holds only for the footage domain above. Historical broadcast footage (2000, 2013) is a different domain: there these detectors are at most `EXPERIMENTAL` until a labelled segment of that footage is evaluated.",
        "- No tracking data exists; no distance, speed, possession share, pitch control or team-shape statistic is produced.",
        "- Team values on verified rows are side labels copied from the reference annotation, not identity resolution.",
        "- `canonical_event_count=UNKNOWN`, `production_release=false`.",
        "",
    ]
    (out / "validation_measurement_report_v1.md").write_text("\n".join(lines), encoding="utf-8")
    return {k: summary[k] for k in ("status", "footage_domain", "heldout_videos", "capability_admission_heldout")} | {"heldout_pooled": pooled}
