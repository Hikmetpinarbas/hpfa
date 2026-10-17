"""Historical Video Intelligence Lite V1 — run orchestration and measurement.

Usage (Colab or any Linux host with ffmpeg):

  python pipeline.py --video half1.mp4 --rights-manifest rights.json --out OUT \
      [--reference bas.json --reference-half 1] [--capability capability.json]

Outputs are flat JSON/TSV plus `hpfa_surface/` (verified rows only).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from evaluation import admit_capability, evaluate, load_bas_reference, mark_reference_verified  # noqa: E402
from frame_source import fingerprint, probe  # noqa: E402
from hpfa_export import envelope, write_event_outputs  # noqa: E402
from hvi_contract import DEFAULT_CAPABILITY, EXPERIMENTAL, SUPPORTED  # noqa: E402
from rights_gate import evaluate_rights, load_manifest  # noqa: E402
from stages import PipelineConfig, analyze_window, extract_window, pooled_reference, audio_shot_candidates, merge_candidates, stage_a_scan  # noqa: E402


class ResourceMeter:
    """Wall, CPU (self + ffmpeg children) and peak RSS for a block."""

    def __enter__(self) -> "ResourceMeter":
        self.t0 = time.perf_counter()
        self.s0 = resource.getrusage(resource.RUSAGE_SELF)
        self.c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        return self

    def __exit__(self, *exc: Any) -> None:
        s1 = resource.getrusage(resource.RUSAGE_SELF)
        c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        self.wall_s = time.perf_counter() - self.t0
        self.cpu_self_s = (s1.ru_utime - self.s0.ru_utime) + (s1.ru_stime - self.s0.ru_stime)
        self.cpu_children_s = (c1.ru_utime - self.c0.ru_utime) + (c1.ru_stime - self.c0.ru_stime)
        self.peak_rss_self_mb = s1.ru_maxrss / 1024.0
        self.peak_rss_children_mb = c1.ru_maxrss / 1024.0

    def as_dict(self) -> dict[str, float]:
        return {
            "wall_s": round(self.wall_s, 3),
            "cpu_python_s": round(self.cpu_self_s, 3),
            "cpu_ffmpeg_children_s": round(self.cpu_children_s, 3),
            "peak_rss_python_mb": round(self.peak_rss_self_mb, 1),
            "peak_rss_ffmpeg_child_max_mb": round(self.peak_rss_children_mb, 1),
        }


def host_info() -> dict[str, Any]:
    gpu = None
    try:
        import subprocess

        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception:
        gpu = None
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "gpu": gpu,
        "colab": "COLAB_RELEASE_TAG" in os.environ or "google.colab" in sys.modules,
    }


def resolve_capability(capability: dict[str, Any] | None, domain: str) -> dict[str, str]:
    """Capability statuses for this run.

    Accepts either {event_type: status} or an admission report
    {"validated_domain": ..., "capability": {event_type: {"status": ...}}}.
    SUPPORTED status never transfers to a different footage domain: it is
    capped at EXPERIMENTAL there.
    """
    resolved = dict(DEFAULT_CAPABILITY)
    if not capability:
        return resolved
    validated_domain = capability.get("validated_domain") if isinstance(capability.get("validated_domain"), str) else None
    items = capability.get("capability", capability)
    for event_type, value in items.items():
        if event_type not in resolved:
            continue
        status = value.get("status") if isinstance(value, dict) else value
        if status == SUPPORTED and validated_domain != domain:
            status = EXPERIMENTAL
        resolved[event_type] = status
    return resolved


def run(
    video: str,
    rights_manifest: dict[str, Any],
    out_dir: str,
    cfg: PipelineConfig | None = None,
    reference: list[dict[str, Any]] | None = None,
    period: str = "UNKNOWN",
    capability: dict[str, str] | None = None,
    video_id: str | None = None,
    domain: str = "UNDECLARED",
) -> dict[str, Any]:
    cfg = cfg or PipelineConfig()
    cfg.capability = resolve_capability(capability, domain)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rights = evaluate_rights(rights_manifest)
    if not rights["processing_allowed"]:
        payload = envelope("FAIL_CLOSED", rights_gate=rights, hard_block_hits=rights["hard_block_hits"])
        (out / "video_run_report_v1.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload

    info = probe(video)
    fp = fingerprint(video)
    ctx = {
        "source_video_id": video_id or rights_manifest.get("video_id") or Path(video).stem,
        "source_fingerprint": fp,
        "rights_manifest_id": rights_manifest["manifest_id"],
        "period": period,
    }

    with ResourceMeter() as meter_a:
        scan = stage_a_scan(video, cfg, fp)
    windows = scan["triage_windows"] + scan["random_audit_windows"]
    with ResourceMeter() as meter_b:
        extracted = [extract_window(video, w, cfg) for w in windows]
        play_ref = pooled_reference(extracted)
        window_reports = [analyze_window(x, play_ref, scan, cfg, ctx) for x in extracted]
    raw_events = [e for r in window_reports for e in r["events"]] + audio_shot_candidates(scan, cfg, ctx)
    events = merge_candidates(raw_events, cfg.merge_tolerance_s)

    # Events seen only inside random audit windows are flagged for review:
    # they measure triage misses, they are not extra evidence.
    for e in events:
        origins = set(e["features"].get("merged_origins") or [e["features"].get("window_origin")])
        e["features"]["seen_in_random_audit_only"] = origins == {"RANDOM_AUDIT"}

    evaluation = None
    capability_report = None
    if reference is not None:
        evaluation = evaluate(events, reference, duration_s=info.duration_s, triage_windows=scan["triage_windows"], audit_windows=scan["random_audit_windows"])
        capability_report = {
            "validated_domain": domain,
            "validation_video_id": ctx["source_video_id"],
            "validation_fingerprint": fp,
            "config_used": cfg.to_dict() | {"capability": None},
            "note": "Admission from this run's metrics. Apply it only to OTHER videos (held-out); in-sample use is optimistic.",
            "capability": admit_capability(evaluation["per_event_type"]),
        }
        events = mark_reference_verified(events, reference, reference_source=rights_manifest.get("reference_label_source", "REFERENCE_LABELS"))

    processed_s = sum(w["end_s"] - w["start_s"] for w in windows)
    measurement = {
        "video_duration_s": info.duration_s,
        "video_native_fps": info.fps,
        "video_resolution": [info.width, info.height],
        "stage_a": {
            "mode": scan["signal"],
            "bin_s": cfg.a_bin_s,
            "analysis_width_px": cfg.a_width,
            "samples": scan["samples"],
            "effective_sample_rate_hz": scan["effective_sample_rate_hz"],
            "resources": meter_a.as_dict(),
            "realtime_factor": round(info.duration_s / meter_a.wall_s, 2) if meter_a.wall_s else None,
        },
        "stage_b": {
            "fps": cfg.b_fps,
            "analysis_width_px": cfg.b_width,
            "windows_triage": len(scan["triage_windows"]),
            "windows_random_audit": len(scan["random_audit_windows"]),
            "seconds_processed": round(processed_s, 3),
            "coverage_fraction": round(processed_s / info.duration_s, 4) if info.duration_s else None,
            "frames": sum(r["frames"] for r in window_reports),
            "pooled_play_reference_activity": round(play_ref, 6),
            "resources": meter_b.as_dict(),
        },
        "total_wall_s": round(meter_a.wall_s + meter_b.wall_s, 3),
        "total_realtime_factor": round(info.duration_s / (meter_a.wall_s + meter_b.wall_s), 2),
        "host": host_info(),
    }
    meta = {
        "rights_gate": rights,
        "config": cfg.to_dict(),
        "video": ctx | {"duration_s": info.duration_s, "footage_domain": domain},
        "measurement": measurement,
        "evaluation": evaluation,
        "capability_from_this_run": capability_report,
    }
    paths = write_event_outputs(out, events, meta)
    scan_slim = {k: v for k, v in scan.items() if k != "series"}
    (out / "video_stage_a_scan_v1.json").write_text(json.dumps(scan_slim, indent=2, sort_keys=True), encoding="utf-8")
    (out / "video_stage_a_series_v1.json").write_text(json.dumps(scan["series"]), encoding="utf-8")
    report = envelope(
        "PASS" if evaluation is not None else "REVIEW_REQUIRED",
        rights_gate=rights,
        measurement=measurement,
        evaluation=evaluation,
        capability_from_this_run=capability_report,
        outputs=paths,
        event_candidates=len(events),
        hard_block_hits=[],
    )
    (out / "video_run_report_v1.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="HPFA Historical Video Intelligence Lite V1")
    p.add_argument("--video", required=True)
    p.add_argument("--rights-manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--reference")
    p.add_argument("--reference-half", type=int, default=1)
    p.add_argument("--period", default="UNKNOWN")
    p.add_argument("--capability", help="JSON {event_type: status} from a held-out validation run")
    p.add_argument("--config", help="JSON overrides for PipelineConfig")
    p.add_argument("--domain", default="UNDECLARED", help="footage domain, e.g. PANORAMIC_FIXED_AMATEUR or BROADCAST_SD_ARCHIVE")
    a = p.parse_args()
    cfg = PipelineConfig(**(json.loads(Path(a.config).read_text()) if a.config else {}))
    ref = load_bas_reference(a.reference, a.reference_half) if a.reference else None
    cap = json.loads(Path(a.capability).read_text()) if a.capability else None
    report = run(a.video, load_manifest(a.rights_manifest), a.out, cfg, ref, a.period, cap, domain=a.domain)
    print(json.dumps({k: report.get(k) for k in ("status", "event_candidates", "hard_block_hits")}, indent=2))
    return 2 if report.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
