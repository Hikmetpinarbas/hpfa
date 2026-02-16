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

GENERIC_NAMES = {
    # isim olarak çok jenerik -> false positive
    "engine","src","tests","demo","schemas","configs","contracts","canon",
}

def should_skip_dir(p: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in p.parts)

def scan_needles(needles):
    hits = {n: [] for n in needles}
    pats = {n: re.compile(re.escape(n)) for n in needles}

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
            for n, pat in pats.items():
                if pat.search(txt):
                    hits[n].append(str(fp))
    return hits

def main():
    if not PROJ.exists():
        print("[FAIL] missing:", PROJ)
        raise SystemExit(2)

    # 1) PROJ path hard reference var mı?
    base_needles = [
        str(PROJ),
        "/HP_PROJELERI/",
        "HP_PROJELERI/",
    ]
    base_hits = scan_needles(base_needles)
    print("== BASE PATH REFERENCES ==")
    for n in base_needles:
        print(f"[HITS] {n} -> {len(base_hits[n])}")
        for s in base_hits[n][:12]:
            print("  -", s)
    print()

    # 2) Sadece “non-generic” klasör isimleri için path+name kontrolü
    candidates = [
        d for d in PROJ.iterdir()
        if d.is_dir() and d.name not in {"HP-Motor-main", "HP_ARCHIVES"}
    ]

    strict_items = []
    for d in sorted(candidates, key=lambda x: x.name.lower()):
        name = d.name
        if name in GENERIC_NAMES:
            continue
        # kanıt: tam path veya PROJ altında geçiş
        needles = [
            str(d),
            f"HP_PROJELERI/{name}",
            f"/HP_PROJELERI/{name}",
        ]
        hits = scan_needles(needles)
        n_hits = sum(len(v) for v in hits.values())
        strict_items.append((name, str(d), n_hits, {k: v[:8] for k, v in hits.items()}))

    print("== STRICT FOLDER REFERENCES (non-generic names) ==")
    for name, path, n_hits, sample in sorted(strict_items, key=lambda x: (-x[2], x[0].lower())):
        tag = "USED" if n_hits > 0 else "UNUSED"
        print(f"[{tag}] {name:24s} hits={n_hits}")
        if n_hits:
            print("  path:", path)
            for k, v in sample.items():
                if v:
                    print("  needle:", k)
                    for s in v:
                        print("    -", s)
    print()

    outp = HOME / "hpfa" / "_diag" / "hp_projeleri_reference_audit_strict.tsv"
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf-8") as f:
        f.write("name\tpath\thits\n")
        for name, path, n_hits, _ in strict_items:
            f.write(f"{name}\t{path}\t{n_hits}\n")

    print("[OK] wrote:", outp)

if __name__ == "__main__":
    main()
