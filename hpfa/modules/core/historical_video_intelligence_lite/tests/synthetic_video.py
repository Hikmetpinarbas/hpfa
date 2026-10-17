"""Deterministic synthetic pitch video with scripted dead-ball periods.

Engineering fixture only: it proves the pipeline mechanics, not football
detection accuracy. Accuracy evidence must come from real labelled footage.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

STOPS = ((40.0, 52.0), (100.0, 108.0), (150.0, 215.0))
DURATION_S = 240
RESTARTS = tuple(end for _, end in STOPS)


def write_synthetic_video(path: Path, width: int = 320, height: int = 180, fps: int = 25) -> Path:
    rng = np.random.default_rng(1)
    n = 22
    pos = rng.uniform([20, 20], [width - 20, height - 20], (n, 2))
    vel = rng.normal(0, 2.5, (n, 2))
    proc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
         "-g", "50", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(path)],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    for i in range(fps * DURATION_S):
        t = i / fps
        stopped = any(a <= t < b for a, b in STOPS)
        frame = np.zeros((height, width, 3), np.uint8)
        frame[...] = (40, 130, 40)
        frame[::30, :, :] = 200
        vel += rng.normal(0, 0.4, (n, 2))
        vel = np.clip(vel, -4, 4)
        pos += vel * (0.03 if stopped else 1.0)
        pos = np.clip(pos, [5, 5], [width - 6, height - 6])
        for k, (x, y) in enumerate(pos.astype(int)):
            frame[y - 4:y + 4, x - 2:x + 2] = (220, 30, 30) if k < 11 else (240, 240, 240)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    return path


def bas_reference_json(path: Path) -> Path:
    """BAS-format labels consistent with the scripted video (half 1)."""
    import json

    def ann(t: float, label: str, team: str = "left") -> dict:
        ms = int(t * 1000)
        return {"gameTime": f"1 - {int(t) // 60:02d}:{int(t) % 60:02d}", "position": str(ms), "label": label, "team": team, "player_id": None, "visibility": "visible"}

    anns = [ann(10, "Pass"), ann(38, "Out"), ann(52.2, "Throw In", "right"), ann(60, "Pass"), ann(99, "Pass"),
            ann(108.3, "Free Kick"), ann(120, "Pass"), ann(149, "Shot"), ann(149, "Goal"), ann(215.2, "Pass", "right"), ann(225, "Pass")]
    path.write_text(json.dumps({"UrlLocal": "synthetic", "UrlYoutube": None, "annotations": anns}), encoding="utf-8")
    return path
