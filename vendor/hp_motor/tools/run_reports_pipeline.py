import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sh(cmd: str) -> None:
    r = subprocess.run(cmd, shell=True, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    pages_dir = ROOT / "artifacts/reports/pages"
    tables_dir = ROOT / "artifacts/reports/tables"
    norm_dir = ROOT / "artifacts/reports/normalized"

    pages_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    norm_dir.mkdir(parents=True, exist_ok=True)

    if not any(pages_dir.glob("*.jsonl")):
        print("OK: pages missing -> python tools/extract_report_pages.py")
        sh("python tools/extract_report_pages.py")
    else:
        print("OK: pages present -> skip extract_report_pages.py")

    if not any(tables_dir.glob("*__tables_raw.csv")):
        print("OK: tables_raw missing -> python tools/extract_report_tables_raw.py")
        sh("python tools/extract_report_tables_raw.py")
    else:
        print("OK: tables_raw present -> skip extract_report_tables_raw.py")

    print("OK: normalize -> python tools/report_tables_normalize.py")
    sh("python tools/report_tables_normalize.py")

    print("OK: reports pipeline complete")

if __name__ == "__main__":
    main()
