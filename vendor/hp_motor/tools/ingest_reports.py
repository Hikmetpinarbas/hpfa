import os, re, json, shutil, hashlib
from datetime import datetime

INCOMING = "data/reports/_incoming"
ARCHIVE_ROOT = "data/reports/tournament_reports"
OUT_ROOT = "artifacts/reports"

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_dirname(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"

def infer_comp_season(filename: str):
    base = filename
    season = "unknown"
    m = re.search(r"(20\d{2})\s*-\s*(20\d{2})", base)
    if m:
        season = f"{m.group(1)}-{m.group(2)}"
    comp = re.sub(r"\(.*?\)", "", base)
    comp = re.sub(r"(20\d{2})\s*-\s*(20\d{2})", "", comp)
    comp = comp.replace(".pdf", "").strip(" -_.")
    comp = re.sub(r"\s+", " ", comp).strip()
    return comp or "unknown", season

def main():
    os.makedirs(INCOMING, exist_ok=True)
    os.makedirs(ARCHIVE_ROOT, exist_ok=True)
    os.makedirs(OUT_ROOT, exist_ok=True)

    pdfs = [x for x in os.listdir(INCOMING) if x.lower().endswith(".pdf")]
    if not pdfs:
        print("[ingest] incoming boş:", INCOMING)
        return

    index = []
    for fn in sorted(pdfs):
        src = os.path.join(INCOMING, fn)
        comp, season = infer_comp_season(fn)
        comp_dir = safe_dirname(comp)
        season_dir = safe_dirname(season)

        dest_dir = os.path.join(ARCHIVE_ROOT, comp_dir, season_dir)
        os.makedirs(dest_dir, exist_ok=True)
        dest_pdf = os.path.join(dest_dir, fn)

        shutil.copy2(src, dest_pdf)

        sha = sha256_file(dest_pdf)
        out_dir = os.path.join(OUT_ROOT, comp_dir, season_dir, safe_dirname(fn))
        os.makedirs(out_dir, exist_ok=True)

        manifest = {
            "ingested_at": datetime.utcnow().isoformat() + "Z",
            "source_filename": fn,
            "competition": comp,
            "season": season,
            "sha256": sha,
            "pdf_path": dest_pdf,
            "parse": {"pages_txt": None, "note": "text extraction not run yet"},
        }

        man_path = os.path.join(out_dir, "manifest.json")
        with open(man_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        index.append({
            "competition": comp,
            "season": season,
            "filename": fn,
            "sha256": sha,
            "pdf_path": dest_pdf,
            "manifest": man_path,
        })

        print(f"[ingest] OK | {comp} | {season} | {fn}")

    idx_path = os.path.join(OUT_ROOT, "index_reports.json")
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("[ingest] index:", idx_path)

if __name__ == "__main__":
    main()
