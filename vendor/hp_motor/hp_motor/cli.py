import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from hp_motor.pipeline.run_pipeline import run as run_pipeline
from hp_motor.library import library_health
from hp_motor.library.loader import _resolve


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hp_motor", description="HP Motor Lite Core CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Run lite-core pipeline and output report json")
    r.add_argument("--events", required=True, help="Path to events (.json/.jsonl/.csv)")
    r.add_argument("--out", required=True, help="Output report path (json)")
    r.add_argument("--run-dir", default=None, help="Run directory (writes hp_report.json inside)")
    r.add_argument("--vendor", default="generic", help="Vendor mapping key")
    return p


def main() -> int:
    args = build_parser().parse_args()

    if args.cmd == "run":
        events_path = Path(args.events)
        report = run_pipeline(events_path, vendor=args.vendor)

        if args.run_dir:
            run_dir = Path(args.run_dir)
            run_dir.mkdir(parents=True, exist_ok=True)
            out = run_dir / "hp_report.json"
        else:
            out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # validation report (P1)
        lib_h = library_health()
        validation = {
            "run_ts": datetime.now(timezone.utc).isoformat(),
            "python": sys.version.split()[0],
            "events_path": str(events_path),
            "vendor_key": args.vendor,
            "out_report_path": str(out),
            "report_keys": list(report.keys()),
            "events_summary": report.get("events_summary", {}),
                        "registry_paths": {
                "vendor_mappings": str(_resolve("registry/vendor_mappings_compiled.json")[0]),
                "metric_registry": str(_resolve("registry/metric_registry.json")[0]),
            },
            "library_health": {
                "status": lib_h.status,
                "flags": list(lib_h.flags),
                "roots_checked": list(lib_h.roots_checked),
            },
        }

        vout = Path(str(out) + ".validation.json")
        vout.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"OK: wrote {out}")
        print(f"OK: wrote {vout}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
