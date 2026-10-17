"""Two-stage video processing.

Stage A (triage) decodes the whole video cheaply (keyframes or low fps, small
frames) and proposes windows: dead-ball/restart patterns, audio peaks and
broadcast cut clusters. A seeded random sample of windows is always added so
the miss rate of triage can be estimated without bias.

Stage B (detail) decodes only the selected windows at higher fps/resolution and
emits event candidates. Detectors here use visible-activity patterns only;
they do not track players or the ball.
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from frame_source import audio_rms, iter_frames, packet_series, probe
from hvi_contract import NOT_SUPPORTED, make_event
from signals import SignalExtractor, low_segments, robust_z, rolling_median

DETECTOR_VERSION = "v1"


@dataclass
class PipelineConfig:
    # Stage A
    a_bin_s: float = 1.0
    a_visual_keyframes: bool = False
    use_keyframe_cut_proxy: bool = False
    a_width: int = 192
    a_smooth_s: float = 4.0
    reference_window_s: float = 180.0
    stop_ratio: float = 0.55
    min_stoppage_s: float = 6.0
    window_pre_s: float = 12.0
    window_post_s: float = 8.0
    max_triage_fraction: float = 0.45
    audio_peak_z: float = 3.5
    cut_threshold: float = 0.5
    # Random audit sample
    random_fraction: float = 0.08
    random_window_s: float = 30.0
    seed: int = 20260417
    # Stage B
    b_fps: float = 5.0
    b_width: int = 384
    b_smooth_s: float = 1.2
    b_stop_ratio: float = 0.55
    b_min_stoppage_s: float = 4.0
    restart_rise_ratio: float = 0.8
    goal_min_stoppage_s: float = 45.0
    merge_tolerance_s: float = 4.0
    compensate_camera: bool = True
    threads: int = 0
    capability: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------- Stage A

def _series(signals: list) -> dict[str, np.ndarray]:
    return {
        "t": np.array([s.t for s in signals], dtype=np.float64),
        "motion": np.array([s.motion for s in signals], dtype=np.float32),
        "active": np.array([s.active_fraction for s in signals], dtype=np.float32),
        "cut": np.array([s.cut for s in signals], dtype=np.float32),
        "green": np.array([s.green for s in signals], dtype=np.float32),
        "shift": np.array([s.shift for s in signals], dtype=np.float32),
        "cx": np.array([s.cx for s in signals], dtype=np.float32),
        "cy": np.array([s.cy for s in signals], dtype=np.float32),
    }


def _activity(series: dict[str, np.ndarray], smooth_s: float) -> np.ndarray:
    t = series["t"]
    if len(t) < 2:
        return series["active"].copy()
    dt = float(np.median(np.diff(t))) or 1.0
    k = max(1, int(round(smooth_s / dt)) | 1)
    return rolling_median(series["active"].astype(np.float64), k)


def _reference(t: np.ndarray, act: np.ndarray, window_s: float) -> np.ndarray:
    """Local in-play activity level: rolling 75th percentile."""
    if len(t) < 2:
        return act.copy()
    dt = float(np.median(np.diff(t))) or 1.0
    k = max(3, int(round(window_s / dt)) | 1)
    if k >= len(act):
        return np.full(len(act), float(np.percentile(act, 75)))
    pad = k // 2
    xp = np.pad(act, (pad, k - 1 - pad), mode="reflect")
    win = np.lib.stride_tricks.sliding_window_view(xp, k)
    return np.percentile(win, 75, axis=1)


def _seed_for(cfg: PipelineConfig, fingerprint: str) -> int:
    return int(hashlib.sha256(f"{cfg.seed}|{fingerprint}".encode()).hexdigest()[:12], 16)


def random_audit_windows(duration_s: float, cfg: PipelineConfig, fingerprint: str) -> list[dict[str, Any]]:
    length = min(cfg.random_window_s, duration_s)
    n = max(1, math.ceil(cfg.random_fraction * duration_s / max(length, 1e-9)))
    slots = max(1, int(duration_s // length))
    rng = random.Random(_seed_for(cfg, fingerprint))
    chosen = sorted(rng.sample(range(slots), min(n, slots)))
    return [
        {
            "start_s": round(i * length, 3),
            "end_s": round(min(duration_s, (i + 1) * length), 3),
            "origin": "RANDOM_AUDIT",
            "reasons": ["seeded_uniform_slot_sample"],
            "priority": 0.0,
        }
        for i in chosen
    ]


def _merge_windows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows = sorted(windows, key=lambda w: w["start_s"])
    merged: list[dict[str, Any]] = []
    for w in windows:
        if merged and w["start_s"] <= merged[-1]["end_s"]:
            last = merged[-1]
            last["end_s"] = max(last["end_s"], w["end_s"])
            last["reasons"] = sorted(set(last["reasons"]) | set(w["reasons"]))
            last["priority"] = max(last["priority"], w["priority"])
            last["stoppages"] = last.get("stoppages", []) + w.get("stoppages", [])
        else:
            merged.append(dict(w))
    return merged


def packet_activity(path: str, bin_s: float) -> dict[str, np.ndarray]:
    """Per-bin mean inter-frame packet bytes + keyframe count (no decoding)."""
    pk = packet_series(path)
    if len(pk["t"]) == 0:
        return {"t": np.array([]), "active": np.array([]), "keys": np.array([])}
    edges = np.arange(0.0, float(pk["t"][-1]) + bin_s, bin_s)
    idx = np.clip(np.digitize(pk["t"], edges) - 1, 0, len(edges) - 1)
    n = len(edges)
    inter = ~pk["key"]
    sums = np.bincount(idx[inter], weights=pk["size"][inter], minlength=n)
    cnts = np.bincount(idx[inter], minlength=n)
    keys = np.bincount(idx[pk["key"]], minlength=n)
    active = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
    good = np.isfinite(active)
    if good.any() and not good.all():
        active = np.interp(np.arange(n), np.nonzero(good)[0], active[good])
    return {"t": edges + bin_s / 2, "active": active.astype(np.float64), "keys": keys.astype(np.float64), "packets": int(len(pk["t"]))}


def stage_a_scan(path: str, cfg: PipelineConfig, fingerprint: str) -> dict[str, Any]:
    """Whole-video triage.

    Primary signal (default): compressed-domain inter-frame packet size per
    second — read from the container without decoding. Optional secondary
    signal: decoded keyframes (grass share, histogram cuts).
    """
    info = probe(path)
    t0 = time.perf_counter()
    pa = packet_activity(path, cfg.a_bin_s)
    series: dict[str, np.ndarray] = {"t": pa["t"], "active": pa["active"], "keys": pa["keys"]}
    visual_samples = 0
    if cfg.a_visual_keyframes:
        extractor = SignalExtractor(compensate_camera=cfg.compensate_camera)
        sig = [extractor(t, f) for t, f in iter_frames(path, fps=None, width=cfg.a_width, keyframes_only=True, threads=cfg.threads) if math.isfinite(t)]
        vs = _series(sig)
        visual_samples = len(sig)
        series["kf_t"], series["kf_cut"], series["kf_green"] = vs["t"], vs["cut"], vs["green"]
    decode_s = time.perf_counter() - t0
    t = series["t"]
    duration = info.duration_s or (float(t[-1]) if len(t) else 0.0)
    act = _activity({"t": t, "active": series["active"]}, cfg.a_smooth_s)
    ref = _reference(t, act, cfg.reference_window_s)
    low = act < cfg.stop_ratio * np.maximum(ref, 1e-6)
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 1.0
    stoppages = low_segments(t, low, cfg.min_stoppage_s, max(2.5 * dt, 1.0))

    windows: list[dict[str, Any]] = []
    for s, e in stoppages:
        windows.append(
            {
                "start_s": max(0.0, e - cfg.window_pre_s),
                "end_s": min(duration, e + cfg.window_post_s),
                "origin": "TRIAGE",
                "reasons": ["dead_ball_to_restart_pattern"],
                "priority": float(e - s),
                "stoppages": [{"start_s": round(s, 3), "end_s": round(e, 3), "duration_s": round(e - s, 3)}],
            }
        )

    audio = None
    try:
        audio = audio_rms(path)
    except Exception:  # audio is optional evidence
        audio = None
    audio_peaks: list[float] = []
    if audio is not None:
        at, rms = audio
        z = robust_z(rolling_median(rms.astype(np.float64), 3))
        for i in np.nonzero(z > cfg.audio_peak_z)[0]:
            if not audio_peaks or at[i] - audio_peaks[-1] > 10:
                audio_peaks.append(float(at[i]))
        for p in audio_peaks:
            windows.append({"start_s": max(0.0, p - 10), "end_s": min(duration, p + 6), "origin": "TRIAGE", "reasons": ["audio_energy_peak"], "priority": 5.0})

    if "kf_cut" in series:
        cuts = series["kf_t"][series["kf_cut"] > cfg.cut_threshold]
    else:
        # Off-GOP keyframes (encoder scene-cut decisions) as cut proxies.
        regular = np.median(series["keys"][series["keys"] > 0]) if (series["keys"] > 0).any() else 0
        cuts = t[series["keys"] > max(1.0, regular)] if cfg.use_keyframe_cut_proxy else np.array([])
    for c in cuts:
        windows.append({"start_s": max(0.0, float(c) - 6), "end_s": min(duration, float(c) + 6), "origin": "TRIAGE", "reasons": ["broadcast_cut"], "priority": 1.0})

    merged = _merge_windows(windows)
    budget = cfg.max_triage_fraction * duration
    merged.sort(key=lambda w: -w["priority"])
    kept, used = [], 0.0
    dropped = 0
    for w in merged:
        span = w["end_s"] - w["start_s"]
        if used + span <= budget:
            kept.append(w)
            used += span
        else:
            dropped += 1
    kept.sort(key=lambda w: w["start_s"])
    audit = random_audit_windows(duration, cfg, fingerprint)

    return {
        "video": asdict(info),
        "signal": "packet_interframe_bytes" + ("+keyframe_visual" if cfg.a_visual_keyframes else ""),
        "packets_read": pa.get("packets", 0),
        "visual_keyframe_samples": visual_samples,
        "samples": int(len(t)),
        "effective_sample_rate_hz": round(len(t) / duration, 4) if duration else None,
        "decode_wall_s": round(decode_s, 3),
        "stoppages": [{"start_s": round(s, 3), "end_s": round(e, 3), "duration_s": round(e - s, 3)} for s, e in stoppages],
        "audio_available": audio is not None,
        "audio_peaks_s": audio_peaks,
        "cut_count": int(len(cuts)),
        "triage_windows": kept,
        "triage_windows_dropped_by_budget": dropped,
        "triage_coverage_fraction": round(used / duration, 4) if duration else None,
        "random_audit_windows": audit,
        "random_audit_coverage_fraction": round(sum(w["end_s"] - w["start_s"] for w in audit) / duration, 4) if duration else None,
        "series": {k: v.tolist() for k, v in series.items()} | {"activity": act.tolist(), "reference": ref.tolist()},
    }


# ---------------------------------------------------------------- Stage B

def _stoppage_containing(scan: dict[str, Any], t: float, slack: float = 3.0) -> dict[str, Any] | None:
    for s in scan["stoppages"]:
        if s["start_s"] - slack <= t <= s["end_s"] + slack:
            return s
    return None


def extract_window(path: str, window: dict[str, Any], cfg: PipelineConfig) -> dict[str, Any]:
    """Decode one window at Stage B resolution and return its signal series."""
    t0 = time.perf_counter()
    extractor = SignalExtractor(compensate_camera=cfg.compensate_camera)
    signals = []
    for t, frame in iter_frames(
        path,
        fps=cfg.b_fps,
        width=cfg.b_width,
        start_s=window["start_s"],
        duration_s=window["end_s"] - window["start_s"],
        threads=cfg.threads,
    ):
        signals.append(extractor(t, frame))
    series = _series(signals[1:]) if len(signals) > 1 else _series(signals)
    series["activity"] = _activity(series, cfg.b_smooth_s) if len(series["t"]) else np.array([])
    return {
        "window": {k: window[k] for k in ("start_s", "end_s", "origin", "reasons")},
        "frames": int(len(signals)),
        "effective_sample_rate_hz": round(len(signals) / max(1e-9, window["end_s"] - window["start_s"]), 3),
        "decode_and_signal_wall_s": round(time.perf_counter() - t0, 3),
        "series": series,
    }


def pooled_reference(extracted: list[dict[str, Any]]) -> float:
    """In-play activity level pooled over all Stage B windows of one video."""
    pool = np.concatenate([x["series"]["activity"] for x in extracted if len(x["series"]["activity"])]) if extracted else np.array([])
    return float(np.percentile(pool, 75)) if len(pool) else 0.0


def analyze_window(extracted: dict[str, Any], play_ref: float, scan: dict[str, Any], cfg: PipelineConfig, ctx: dict[str, str]) -> dict[str, Any]:
    series = extracted["series"]
    window = extracted["window"]
    t = series["t"]
    events: list[dict[str, Any]] = []
    if len(t) >= 3:
        act = series["activity"]
        ref = np.full(len(t), max(play_ref, 1e-6))
        low = act < cfg.b_stop_ratio * ref
        dt = 1.0 / cfg.b_fps
        segs = low_segments(t, low, cfg.b_min_stoppage_s, 2.5 * dt)
        cap = cfg.capability
        for s, e in segs:
            after = (t > e) & (t <= e + 3.0)
            if not after.any():
                continue  # restart not visible inside the window
            rise = act[after]
            onset_idx = np.nonzero(after)[0]
            hit = onset_idx[np.argmax(rise >= cfg.restart_rise_ratio * ref[onset_idx])] if (rise >= cfg.restart_rise_ratio * ref[onset_idx]).any() else None
            if hit is None:
                continue
            onset = float(t[hit])
            a_stop = _stoppage_containing(scan, e)
            stop_start = min(s, a_stop["start_s"]) if a_stop else s
            stop_dur = onset - stop_start
            contrast = float(np.clip((act[hit] - act[(t >= s) & (t <= e)].mean()) / (ref[hit] + 1e-6), 0, 3))
            score = float(1 - math.exp(-stop_dur / 20.0)) * 0.6 + 0.4 * min(1.0, contrast / 1.5)
            near = (t >= onset - 1.0) & (t <= onset + 2.0) & np.isfinite(series["cx"])
            cx = float(np.nanmean(series["cx"][near])) if near.any() else float("nan")
            cy = float(np.nanmean(series["cy"][near])) if near.any() else float("nan")
            features = {
                "stoppage_start_s": round(stop_start, 3),
                "stoppage_duration_s": round(stop_dur, 3),
                "activity_contrast": round(contrast, 4),
                "activity_centroid_x": None if math.isnan(cx) else round(cx, 4),
                "activity_centroid_y": None if math.isnan(cy) else round(cy, 4),
                "window_origin": window["origin"],
            }
            events.append(
                make_event(
                    event_type="SET_PIECE_RESTART",
                    video_time_s=onset,
                    detector_id=f"restart_after_dead_ball_{DETECTOR_VERSION}",
                    stage="B",
                    score=score,
                    time_uncertainty_s=max(1.0, 2 * dt),
                    capability_status=cap.get("SET_PIECE_RESTART", NOT_SUPPORTED),
                    features=features,
                    **ctx,
                )
            )
            if stop_dur >= cfg.goal_min_stoppage_s:
                events.append(
                    make_event(
                        event_type="GOAL",
                        video_time_s=stop_start,
                        video_time_end_s=onset,
                        detector_id=f"goal_by_long_stoppage_then_restart_{DETECTOR_VERSION}",
                        stage="B",
                        score=float(1 - math.exp(-(stop_dur - cfg.goal_min_stoppage_s) / 30.0)) * 0.5 + 0.2,
                        time_uncertainty_s=8.0,
                        event_subtype="INFERRED_FROM_RESTART_PATTERN",
                        capability_status=cap.get("GOAL", NOT_SUPPORTED),
                        features=features,
                        **ctx,
                    )
                )
    return {k: v for k, v in extracted.items() if k != "series"} | {"events": events}


def audio_shot_candidates(scan: dict[str, Any], cfg: PipelineConfig, ctx: dict[str, str]) -> list[dict[str, Any]]:
    """EXPERIMENTAL: crowd/commentary energy peaks as shot candidates.

    Audio reaction is a proxy for salience, not an observation of a shot.
    """
    out = []
    for p in scan.get("audio_peaks_s", []):
        out.append(
            make_event(
                event_type="SHOT",
                video_time_s=max(0.0, p - 2.0),
                detector_id=f"audio_salience_peak_{DETECTOR_VERSION}",
                stage="A",
                score=0.3,
                time_uncertainty_s=5.0,
                event_subtype="AUDIO_SALIENCE_PROXY",
                capability_status=cfg.capability.get("SHOT", NOT_SUPPORTED),
                features={"audio_peak_s": p},
                **ctx,
            )
        )
    return out


def merge_candidates(events: list[dict[str, Any]], tolerance_s: float) -> list[dict[str, Any]]:
    """Collapse duplicates from overlapping windows (same type, close time)."""
    out: list[dict[str, Any]] = []
    for ev in sorted(events, key=lambda e: (e["event_type"], e["video_time_s"])):
        if out and out[-1]["event_type"] == ev["event_type"] and abs(ev["video_time_s"] - out[-1]["video_time_s"]) <= tolerance_s:
            if ev["score"] > out[-1]["score"]:
                origins = set(out[-1]["features"].get("merged_origins", [out[-1]["features"].get("window_origin")]))
                ev["features"]["merged_origins"] = sorted(o for o in origins | {ev["features"].get("window_origin")} if o)
                out[-1] = ev
            else:
                origins = set(out[-1]["features"].get("merged_origins", [out[-1]["features"].get("window_origin")]))
                out[-1]["features"]["merged_origins"] = sorted(o for o in origins | {ev["features"].get("window_origin")} if o)
            continue
        out.append(ev)
    return sorted(out, key=lambda e: e["video_time_s"])
