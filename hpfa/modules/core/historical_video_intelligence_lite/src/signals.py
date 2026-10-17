"""Per-frame visual signals (numpy only).

All signals are DERIVED_OBSERVATION proxies of what is visible on screen.
Motion energy is pixel change after global camera-shift compensation; it is
not player speed, distance or any tracking quantity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def gray(frame: np.ndarray) -> np.ndarray:
    f = frame.astype(np.float32)
    return 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]


def pitch_mask(frame: np.ndarray) -> np.ndarray:
    """Grass-coloured pixels (works for colour footage only)."""
    f = frame.astype(np.int16)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    return (g > r + 8) & (g > b + 8) & (g > 40)


def phase_shift(a: np.ndarray, b: np.ndarray, min_peak_ratio: float = 8.0) -> tuple[int, int]:
    """Integer global translation of b relative to a (phase correlation).

    Returns (0, 0) when the correlation peak is not distinct (flat or
    periodic texture), so ambiguous frames are not "compensated" wrongly.
    """
    fa = np.fft.rfft2(a - a.mean())
    fb = np.fft.rfft2(b - b.mean())
    cross = fa * np.conj(fb)
    cross /= np.abs(cross) + 1e-9
    corr = np.fft.irfft2(cross, s=a.shape)
    flat = int(np.argmax(corr))
    peak = float(corr.flat[flat])
    if peak < min_peak_ratio * (float(np.abs(corr).mean()) + 1e-9) or peak < 0.05:
        return 0, 0
    dy, dx = np.unravel_index(flat, corr.shape)
    h, w = a.shape
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    return int(dy), int(dx)


def _overlap(a: np.ndarray, b: np.ndarray, dy: int, dx: int) -> tuple[np.ndarray, np.ndarray]:
    h, w = a.shape[:2]
    ya0, ya1 = max(0, dy), min(h, h + dy)
    xa0, xa1 = max(0, dx), min(w, w + dx)
    yb0, yb1 = max(0, -dy), min(h, h - dy)
    xb0, xb1 = max(0, -dx), min(w, w - dx)
    return a[ya0:ya1, xa0:xa1], b[yb0:yb1, xb0:xb1]


def histogram(g: np.ndarray, bins: int = 32) -> np.ndarray:
    hist, _ = np.histogram(g, bins=bins, range=(0, 256))
    return hist.astype(np.float32) / max(1, g.size)


@dataclass
class FrameSignal:
    t: float
    motion: float  # mean |diff| after shift compensation, on pitch pixels
    active_fraction: float  # share of compensated pixels with |diff| > threshold
    cut: float  # histogram L1 distance to previous frame (0..2)
    green: float  # grass-coloured pixel share
    shift: float  # global camera translation magnitude (pixels at analysis width)
    cx: float  # activity centroid x (0..1), NaN if no activity
    cy: float  # activity centroid y (0..1)


class SignalExtractor:
    """Stateful extractor; feed frames in time order."""

    def __init__(self, compensate_camera: bool = True, diff_threshold: float = 18.0):
        self.compensate = compensate_camera
        self.thr = diff_threshold
        self.prev_g: np.ndarray | None = None
        self.prev_h: np.ndarray | None = None

    def reset(self) -> None:
        self.prev_g = None
        self.prev_h = None

    def __call__(self, t: float, frame: np.ndarray) -> FrameSignal:
        g = gray(frame)
        h = histogram(g)
        mask = pitch_mask(frame)
        green = float(mask.mean())
        if self.prev_g is None:
            self.prev_g, self.prev_h = g, h
            return FrameSignal(t, 0.0, 0.0, 0.0, green, 0.0, float("nan"), float("nan"))
        cut = float(np.abs(h - self.prev_h).sum())
        dy = dx = 0
        if self.compensate:
            dy, dx = phase_shift(g, self.prev_g)
        cur, prev = _overlap(g, self.prev_g, dy, dx)
        m_cur, _ = _overlap(mask, mask, dy, dx)
        diff = np.abs(cur - prev)
        region = m_cur if m_cur.mean() > 0.2 else np.ones_like(m_cur, dtype=bool)
        vals = diff[region]
        motion = float(vals.mean()) if vals.size else 0.0
        active = (diff > self.thr) & region
        active_fraction = float(active.mean()) if active.size else 0.0
        if active.any():
            ys, xs = np.nonzero(active)
            cy = float(ys.mean() / max(1, active.shape[0] - 1))
            cx = float(xs.mean() / max(1, active.shape[1] - 1))
        else:
            cx = cy = float("nan")
        self.prev_g, self.prev_h = g, h
        return FrameSignal(t, motion, active_fraction, cut, green, float(np.hypot(dy, dx)), cx, cy)


def rolling_median(x: np.ndarray, k: int) -> np.ndarray:
    if k <= 1 or len(x) == 0:
        return x.copy()
    pad = k // 2
    xp = np.pad(x, (pad, k - 1 - pad), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(xp, k)
    return np.median(windows, axis=1)


def robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x) if len(x) else 0.0
    mad = np.median(np.abs(x - med)) if len(x) else 0.0
    return (x - med) / (1.4826 * mad + 1e-9)


def low_segments(times: np.ndarray, low: np.ndarray, min_len_s: float, max_gap_s: float) -> list[tuple[float, float]]:
    """Contiguous runs where `low` is True, bridging gaps <= max_gap_s."""
    segs: list[tuple[float, float]] = []
    start = None
    last = None
    for t, flag in zip(times, low):
        if flag:
            if start is None:
                start = t
            elif last is not None and t - last > max_gap_s:
                if last - start >= min_len_s:
                    segs.append((float(start), float(last)))
                start = t
            last = t
        elif start is not None and last is not None and t - last > max_gap_s:
            if last - start >= min_len_s:
                segs.append((float(start), float(last)))
            start = None
            last = None
    if start is not None and last is not None and last - start >= min_len_s:
        segs.append((float(start), float(last)))
    return segs
