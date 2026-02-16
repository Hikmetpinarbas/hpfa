import re
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
PROJ = HOME / "HP_PROJELERI"

ROOTS = [
    HOME / "hpfa",
    HOME / "HPFA_MASTER" / "base" / "hpfa-monorepo",
    PROJ / "HP-Motor-main",
]

EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", "build", "dist", ".pytest_cache",
    "_out", "out", "_diag", "HP_ARCHIVES",
}

TEXT_FILE_EXTS = {".py", ".sh", ".toml", ".yml", ".yaml", ".json", ".md", ".txt"}

def should_skip_dir(p: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in p.parts)

def scan_text_refs(needle: str):
    hits = []
    pat = re.compile(re.escape(needle))
    for root in ROOTS:
        if not root.exists():
            continue
        for fp in root.rglob("*"):
            if fp.is_dir():
                continue
            if should_skip_dir(fp.parent):
                continue
            if fp.suffix.lower() not in TEXT_FILE_EXTS:
                continue
            try:
                txt = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if pat.search(txt):
                hits.append(str(fp))
    return hits

def main():
    if not PROJ.exists():
        print("[FAIL] missing:", PROJ)
        raise SystemExit(2)

    candidates = [
        d for d in PROJ.iterdir()
        if d.is_dir() and d.name not in {"HP-Motor-main", "HP_ARCHIVES"}
    ]

    print("[OK] PROJ:", PROJ)
    print("[OK] ROOTS:")
    for r in ROOTS:
        print(" -", r)

    results = []
    for d in sorted(candidates, key=lambda x: x.name.lower()):
        name = d.name
        hits = scan_text_refs(name)
        results.append((name, len(hits), hits[:10]))

    print("\n== HP_PROJELERI reference audit (by folder name) ==")
    for name, n, sample in sorted(results, key=lambda x: (-x[1], x[0].lower())):
        tag = "USED" if n > 0 else "UNUSED"
        print(f"[{tag}] {name:24s} refs={n}")
        for s in sample:
            print("   -", s)

    outp = HOME / "hpfa" / "_diag" / "hp_projeleri_reference_audit.tsv"
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8") as f:
        f.write("name\trefs\tsample_files\n")
        for name, n, sample in results:
            f.write(f"{name}\t{n}\t{';'.join(sample)}\n")

    print("\n[OK] wrote:", outp)

if __name__ == "__main__":
    main()
