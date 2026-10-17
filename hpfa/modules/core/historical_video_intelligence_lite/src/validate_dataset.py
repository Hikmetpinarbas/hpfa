"""Calibrate on one labelled half, evaluate on held-out halves, write evidence.

Expected layout (BAS-format datasets, e.g. an openly licensed panoramic set):

  DATA/bas/<match>/<match>_12_class_events.json
  DATA/videos/<match>/<match>_panorama_1st_half.mp4 (or _2nd_half)

  python validate_dataset.py --data DATA --manifest rights.json \
      --calibrate M1:1 --test M2:1 --test M3:2 --out OUT [--segment-s 900]
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from calibration import calibrate  # noqa: E402
from evaluation import load_bas_reference  # noqa: E402
from pipeline import finish, prepare, resolve_capability  # noqa: E402
from report import write_report  # noqa: E402
from rights_gate import load_manifest  # noqa: E402
from stages import PipelineConfig  # noqa: E402

HALF_NAME = {1: "1st", 2: "2nd"}


def locate(data: Path, match: str, half: int) -> tuple[Path, Path]:
    video = data / "videos" / match / f"{match}_panorama_{HALF_NAME[half]}_half.mp4"
    labels = data / "bas" / match / f"{match}_12_class_events.json"
    return video, labels


def segment(video: Path, seconds: float | None, out_dir: Path) -> Path:
    """Stream-copy the first `seconds` of a video (no re-encode, keyframe-aligned)."""
    if not seconds:
        return video
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{video.stem}_first{int(seconds)}s.mp4"
    if not target.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(video), "-t", f"{seconds:.3f}", "-c", "copy", "-an", "-movflags", "+faststart", str(target)], check=True)
    return target


def clip_reference(refs: list[dict[str, Any]], duration_s: float) -> list[dict[str, Any]]:
    return [r for r in refs if r["t"] <= duration_s]


def parse_item(text: str) -> tuple[str, int]:
    match, _, half = text.partition(":")
    return match, int(half or 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--calibrate", required=True, help="MATCH:HALF")
    ap.add_argument("--test", action="append", required=True, help="MATCH:HALF (repeatable)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--domain", default="PANORAMIC_FIXED_AMATEUR")
    ap.add_argument("--segment-s", type=float, default=None, help="analyse only the first N seconds of each half")
    ap.add_argument("--config", help="JSON PipelineConfig overrides")
    ap.add_argument("--no-calibration", action="store_true", help="use config as-is (no threshold search)")
    a = ap.parse_args()

    data, out = Path(a.data), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(a.manifest)
    base = PipelineConfig(**(json.loads(Path(a.config).read_text()) if a.config else {}))
    seg_dir = out / "_segments"

    # ---- calibration
    cm, ch = parse_item(a.calibrate)
    cvideo, clabels = locate(data, cm, ch)
    cvideo = segment(cvideo, a.segment_s, seg_dir)
    base.capability = resolve_capability(None, a.domain)
    prep = prepare(str(cvideo), manifest, base, period=str(ch), video_id=f"{cm}_h{ch}")
    if not prep["rights"]["processing_allowed"]:
        print(json.dumps(prep["rights"], indent=2))
        return 2
    crefs = clip_reference(load_bas_reference(clabels, ch), prep["info"].duration_s)
    if a.no_calibration:
        cal = {"best_params": {}, "trials": [], "trial_count": 0, "config": base, "note": "calibration skipped"}
    else:
        cal = calibrate(prep, crefs, base)
    tuned: PipelineConfig = cal.pop("config")
    cal_report = finish(prep, tuned, str(out / "calibration" / f"{cm}_h{ch}"), crefs, a.domain, {"role": "CALIBRATION_IN_SAMPLE", "calibration": {k: v for k, v in cal.items() if k != "trials"} | {"top_trials": cal["trials"][:10]}})
    capability = cal_report["capability_from_this_run"]
    (out / "capability_from_calibration_v1.json").write_text(json.dumps(capability, indent=2, sort_keys=True), encoding="utf-8")
    (out / "tuned_config_v1.json").write_text(json.dumps(tuned.to_dict() | {"capability": None}, indent=2, sort_keys=True), encoding="utf-8")

    # ---- held-out
    reports = {"calibration": cal_report, "heldout": []}
    for item in a.test:
        tm, th = parse_item(item)
        if (tm, th) == (cm, ch):
            raise SystemExit("held-out item equals calibration item")
        tvideo, tlabels = locate(data, tm, th)
        tvideo = segment(tvideo, a.segment_s, seg_dir)
        cfg = copy.deepcopy(tuned)
        # Held-out runs use the calibration capability (admission evidence comes
        # from the calibration video, measurement from this video).
        cfg.capability = resolve_capability(capability, a.domain)
        tprep = prepare(str(tvideo), manifest, cfg, period=str(th), video_id=f"{tm}_h{th}")
        trefs = clip_reference(load_bas_reference(tlabels, th), tprep["info"].duration_s)
        reports["heldout"].append(finish(tprep, cfg, str(out / "heldout" / f"{tm}_h{th}"), trefs, a.domain, {"role": "HELDOUT_TEST"}))

    summary = write_report(out, reports, manifest)
    print(json.dumps(summary, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
