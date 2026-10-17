"""ffmpeg-backed frame and audio access.

Only local files (or URLs the operator is entitled to read) are opened. No
downloader, stream ripper or protection bypass is implemented here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np

_PTS = re.compile(r"pts_time:\s*([0-9.+-eE]+)")


def require_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"{tool}_not_found")


@dataclass(frozen=True)
class VideoInfo:
    path: str
    duration_s: float
    fps: float
    width: int
    height: int
    codec: str
    has_audio: bool
    size_bytes: int


def probe(path: str | Path) -> VideoInfo:
    require_ffmpeg()
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(out)
    video = next(s for s in data["streams"] if s.get("codec_type") == "video")
    num, _, den = (video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    duration = float(data["format"].get("duration") or video.get("duration") or 0.0)
    size = int(data["format"].get("size") or (os.path.getsize(path) if os.path.exists(path) else 0))
    return VideoInfo(
        path=str(path),
        duration_s=duration,
        fps=fps,
        width=int(video["width"]),
        height=int(video["height"]),
        codec=str(video.get("codec_name")),
        has_audio=any(s.get("codec_type") == "audio" for s in data["streams"]),
        size_bytes=size,
    )


def fingerprint(path: str | Path, chunk: int = 4 * 1024 * 1024) -> str:
    """Content fingerprint: sha256 over size + first/middle/last chunks.

    This is a sampling fingerprint for large videos, not a full-file hash; the
    contract field is named `source_fingerprint` for that reason.
    """
    p = Path(path)
    size = p.stat().st_size
    h = hashlib.sha256(str(size).encode())
    with p.open("rb") as handle:
        for offset in sorted({0, max(0, size // 2 - chunk // 2), max(0, size - chunk)}):
            handle.seek(offset)
            h.update(handle.read(chunk))
    return "fp256s_" + h.hexdigest()[:32]


def iter_frames(
    path: str | Path,
    *,
    fps: float | None,
    width: int,
    start_s: float = 0.0,
    duration_s: float | None = None,
    keyframes_only: bool = False,
    threads: int = 0,
) -> Iterator[tuple[float, np.ndarray]]:
    """Yield (video_time_s, RGB uint8 frame) at reduced size.

    keyframes_only decodes intra frames only (fast triage); exact keyframe
    timestamps are recovered from the showinfo filter.
    """
    require_ffmpeg()
    info = probe(path)
    height = int(round(info.height * width / info.width / 2) * 2)
    filters = []
    if fps and not keyframes_only:
        filters.append(f"fps={fps}")
    filters.append(f"scale={width}:{height}:flags=area")
    filters.append("format=rgb24")
    if keyframes_only:
        filters.append("showinfo")
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "info" if keyframes_only else "error", "-threads", str(threads)]
    if keyframes_only:
        cmd += ["-skip_frame", "nokey"]
    if start_s > 0:
        cmd += ["-ss", f"{start_s:.3f}"]
    cmd += ["-i", str(path)]
    if duration_s is not None:
        cmd += ["-t", f"{duration_s:.3f}"]
    cmd += ["-an", "-vf", ",".join(filters)]
    if keyframes_only:
        cmd += ["-fps_mode", "passthrough"]
    cmd += ["-f", "rawvideo", "pipe:1"]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pts: list[float] = []
    stderr_tail: list[str] = []
    cond = threading.Condition()

    def _drain() -> None:
        assert proc.stderr is not None
        for raw in proc.stderr:
            line = raw.decode("utf-8", "replace")
            match = _PTS.search(line)
            with cond:
                if match:
                    pts.append(float(match.group(1)))
                else:
                    stderr_tail.append(line)
                    del stderr_tail[:-20]
                cond.notify_all()
        with cond:
            pts.append(float("nan"))  # sentinel: stream closed
            cond.notify_all()

    reader = threading.Thread(target=_drain, daemon=True)
    reader.start()
    frame_bytes = width * height * 3
    index = 0
    try:
        assert proc.stdout is not None
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            frame = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 3)
            if keyframes_only:
                with cond:
                    cond.wait_for(lambda: len(pts) > index, timeout=30)
                    t = pts[index] if index < len(pts) else float("nan")
                t = start_s + t if start_s > 0 else t
            else:
                t = start_s + index / float(fps or info.fps)
            index += 1
            yield t, frame
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        reader.join(timeout=5)
    if proc.returncode not in (0, None, -9) and index == 0:
        raise RuntimeError("ffmpeg_decode_failed:" + "".join(stderr_tail[-5:]))


def audio_rms(path: str | Path, *, hop_s: float = 0.5, rate: int = 8000) -> tuple[np.ndarray, np.ndarray] | None:
    """Mono audio RMS envelope (times, rms). None when no audio stream."""
    info = probe(path)
    if not info.has_audio:
        return None
    raw = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "pipe:1"],
        check=True,
        capture_output=True,
    ).stdout
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    hop = int(rate * hop_s)
    n = len(samples) // hop
    if n == 0:
        return None
    rms = np.sqrt(np.mean(samples[: n * hop].reshape(n, hop) ** 2, axis=1))
    times = (np.arange(n) + 0.5) * hop_s
    return times, rms


def packet_series(path: str | Path) -> dict[str, np.ndarray]:
    """Compressed-domain video packet sizes (no decoding).

    Returns pts_time, size (bytes) and keyframe flag per packet, sorted by pts.
    Inter-frame packet size is a proxy for visible change (motion/residual),
    and depends on encoder settings: compare only within one file.
    """
    require_ffmpeg()
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time,size,flags", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    t, size, key = [], [], []
    for line in proc.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 3 or parts[0] in ("", "N/A"):
            continue
        try:
            t.append(float(parts[0]))
            size.append(int(parts[1]))
        except ValueError:
            continue
        key.append("K" in parts[2])
    order = np.argsort(np.asarray(t))
    return {
        "t": np.asarray(t, dtype=np.float64)[order],
        "size": np.asarray(size, dtype=np.float64)[order],
        "key": np.asarray(key, dtype=bool)[order],
    }
