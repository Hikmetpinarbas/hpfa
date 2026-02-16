from pathlib import Path
from datetime import datetime
import subprocess
import csv

HOME = Path("/data/data/com.termux/files/home")
PROJ = HOME / "HP_PROJELERI"
KEEP_MOTOR = PROJ / "HP-Motor-main"

OUT = HOME / "hpfa" / "_diag" / "hp_projeleri_inventory.tsv"
OUT.parent.mkdir(parents=True, exist_ok=True)

CODE_EXTS = {".py",".sh",".toml",".yml",".yaml",".json",".md",".txt",".ini",".cfg",".ts",".js"}
DATA_EXTS = {".csv",".xml",".parquet",".feather",".xlsx",".xls",".db",".sqlite",".jsonl",".ipynb"}
MEDIA_EXTS = {".mp4",".mov",".mkv",".mp3",".wav",".m4a",".jpg",".jpeg",".png",".webp"}
ARCHIVE_EXTS = {".zip",".tgz",".gz",".tar",".7z",".rar"}

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache", "_out", "out", "_diag", "HP_ARCHIVES"}

def safe_stat(p: Path):
    try:
        st = p.stat()
        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return st.st_size, mtime
    except Exception:
        return 0, "n/a"

def du_bytes(p: Path) -> int:
    try:
        r = subprocess.run(["du", "-sb", str(p)], capture_output=True, text=True, check=False)
        if r.returncode == 0 and r.stdout.strip():
            return int(r.stdout.split()[0])
    except Exception:
        pass
    return safe_stat(p)[0]

def repo_signal(p: Path) -> str:
    if (p / ".git").is_dir(): return "git"
    if (p / "pyproject.toml").is_file(): return "pyproject"
    if (p / "setup.py").is_file(): return "setup.py"
    if (p / "setup.cfg").is_file(): return "setup.cfg"
    return "no"

def should_skip(fp: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in fp.parts)

def norm_ext(f: Path) -> str:
    # "Futbolun-matrixi. txt" gibi -> ". txt" gelir; normalize et
    ext = f.suffix.lower().strip()
    # bazı dosyalarda çift uzantı beklentisi
    if f.name.lower().endswith(".tar.gz"):
        return ".tar.gz"
    return ext

def filetype_mix(p: Path, limit=4000):
    counts = {"code":0, "data":0, "media":0, "archive":0, "other":0}
    scanned = 0

    def add_file(f: Path):
        nonlocal scanned
        scanned += 1
        ext = norm_ext(f)
        if ext in CODE_EXTS: counts["code"] += 1
        elif ext in DATA_EXTS: counts["data"] += 1
        elif ext in MEDIA_EXTS: counts["media"] += 1
        elif ext in ARCHIVE_EXTS: counts["archive"] += 1
        else: counts["other"] += 1

    try:
        if p.is_file():
            add_file(p)
            return scanned, counts

        for fp in p.rglob("*"):
            if fp.is_dir():
                continue
            if should_skip(fp):
                continue
            add_file(fp)
            if scanned >= limit:
                break
    except Exception:
        pass

    return scanned, counts

def label(p: Path, rsignal: str, mix: dict) -> str:
    if p == KEEP_MOTOR:
        return "KEEP_SSOT"
    if p.is_dir() and rsignal != "no":
        return "KEEP_RUNTIME"
    if p.is_file():
        ext = norm_ext(p)
        if ext in CODE_EXTS:
            return "KEEP_RUNTIME"
        return "ARCHIVE"

    code, data, media, arch, other = mix["code"], mix["data"], mix["media"], mix["archive"], mix["other"]
    if (media + arch) >= max(5, code * 2):
        return "ARCHIVE"
    if data >= max(10, code * 2) and code < 50:
        return "ARCHIVE"
    if code >= 50 and (media + arch + data) < code:
        return "KEEP_RUNTIME"
    return "REVIEW"

def main():
    if not PROJ.exists():
        print("[FAIL] missing:", PROJ)
        raise SystemExit(2)

    items = sorted([p for p in PROJ.iterdir()], key=lambda x: x.name.lower())

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow([
            "path","name","kind","size_bytes","mtime","repo_signal",
            "scanned_n","mix_code","mix_data","mix_media","mix_archive","mix_other",
            "label"
        ])

        for p in items:
            kind = "dir" if p.is_dir() else "file"
            sizeb = du_bytes(p)
            _, mtime = safe_stat(p)
            rsignal = repo_signal(p) if p.is_dir() else "no"
            scanned_n, mix = filetype_mix(p, limit=4000)
            lab = label(p, rsignal, mix)
            w.writerow([
                str(p), p.name, kind, sizeb, mtime, rsignal,
                scanned_n, mix["code"], mix["data"], mix["media"], mix["archive"], mix["other"],
                lab
            ])

    print("[OK] wrote:", OUT)

    # hızlı kontrol: kök dosyalarda ARCHIVE var mı?
    print("\n== ROOT FILES labeled ARCHIVE ==")
    import pandas as pd  # type: ignore
    df = pd.read_csv(OUT, sep="\t")
    df_root_files = df[(df["kind"]=="file") & (df["label"]=="ARCHIVE")]
    for _, r in df_root_files.iterrows():
        print(f"- {r['name']}  ({int(r['size_bytes'])/1024:.1f}KB)")

if __name__ == "__main__":
    main()
