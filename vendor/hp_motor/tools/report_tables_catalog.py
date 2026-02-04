from _root import ROOT
import csv
import re
from pathlib import Path
from collections import Counter, defaultdict

TABLES_DIR = Path("artifacts/reports/tables")
OUT_DIR = Path("artifacts/reports/normalized")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# heuristic signatures
SIGS = {
    "goal_timing_tr": re.compile(r"1\.\s*Devre.*0-15.*90\+", re.I),
    "goal_timing_en": re.compile(r"1st\s*Half.*0-15.*90\+", re.I),
    "shots": re.compile(r"\bşut\b|\bshot\b", re.I),
    "xg": re.compile(r"\bxg\b|\bekgol\b", re.I),
    "possession": re.compile(r"\bpossession\b|\btopla oynama\b", re.I),
    "passes": re.compile(r"\bpass\b|\bpas\b", re.I),
    "ppda": re.compile(r"\bppda\b", re.I),
    "press": re.compile(r"\bpressure\b|\bpress\b|\bbaskı\b", re.I),
}

def main():
    files = sorted(TABLES_DIR.glob("*__tables_raw.csv"))
    if not files:
        raise SystemExit("ERR: no *__tables_raw.csv in artifacts/reports/tables")

    per_report = defaultdict(Counter)
    global_sig = Counter()
    header_samples = defaultdict(list)

    for fp in files:
        rid = fp.stem.replace("__tables_raw","")
        with fp.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                kind = (row.get("kind") or "").strip()
                txt = (row.get("text") or "").strip()
                if not txt:
                    continue

                # treat "spaced" lines that look like headers as header candidates
                if kind in ("spaced","numeric"):
                    for name, rx in SIGS.items():
                        if rx.search(txt):
                            per_report[rid][name] += 1
                            global_sig[name] += 1
                            if len(header_samples[name]) < 10:
                                header_samples[name].append((rid, row.get("page_index",""), txt))

    out_txt = OUT_DIR / "tables_catalog.txt"
    with out_txt.open("w", encoding="utf-8") as w:
        w.write("GLOBAL_SIGNATURE_COUNTS\n")
        for k,v in global_sig.most_common():
            w.write(f"{k}\t{v}\n")

        w.write("\nPER_REPORT_SIGNATURES\n")
        for rid, cnt in per_report.items():
            w.write(f"\n[{rid}]\n")
            for k,v in cnt.most_common():
                w.write(f"{k}\t{v}\n")

        w.write("\nHEADER_SAMPLES\n")
        for k, samples in header_samples.items():
            w.write(f"\n== {k} ==\n")
            for rid, pg, txt in samples:
                w.write(f"{rid}\tpage={pg}\t{txt}\n")

    print(f"OK: wrote {out_txt}")

if __name__ == "__main__":
    main()
