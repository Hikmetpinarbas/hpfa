import re, sys, json, subprocess
from pathlib import Path
from importlib import metadata

ROOTS = [
    Path.home() / "hpfa",
    Path.home() / "HPFA_MASTER" / "base" / "hpfa-monorepo",
    Path.home() / "HP_PROJELERI" / "HP-Motor-main",
]

EXCLUDE_DIRS = {
    ".git",".venv","__pycache__","build","dist",".pytest_cache",
    "_out","out","_diag","quarantine",
}
EXCLUDE_DIR_PREFIXES = ("_QUARANTINE_DUPLICATES_", "_HP_GRAVEYARD_", "_HP_QUARANTINE_")

PIP_TO_IMPORT = {
    "pyyaml": "yaml",
    "python-docx": "docx",
    "pypdf": "pypdf",
    "beautifulsoup4": "bs4",
    "scikit-learn": "sklearn",
    "opencv-python": "cv2",
    "pillow": "PIL",
    "python-dateutil": "dateutil",   # <-- FIX
}

def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def pip_list_names():
    out = run([sys.executable, "-m", "pip", "list", "--format=json"])
    j = json.loads(out)
    return sorted({x["name"] for x in j})

def should_skip_dir(p: Path) -> bool:
    parts = set(p.parts)
    if parts & EXCLUDE_DIRS:
        return True
    for part in p.parts:
        if part.startswith(EXCLUDE_DIR_PREFIXES):
            return True
    return False

IMPORT_RE = re.compile(r'^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', re.M)

def scan_imports():
    mods = set()
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if should_skip_dir(p.parent):
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in IMPORT_RE.finditer(txt):
                top = m.group(1).split(".")[0]
                mods.add(top)
    return mods

def reverse_deps():
    # who requires whom (best-effort)
    req_by = {}
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "").lower()
        if not name:
            continue
        requires = dist.requires or []
        for r in requires:
            dep = r.split(";")[0].strip().split()[0].lower().replace("_","-")
            if not dep:
                continue
            req_by.setdefault(dep, set()).add(name)
    return {k: sorted(v) for k, v in req_by.items()}

def main():
    pip_names = pip_list_names()
    imported = scan_imports()
    req_by = reverse_deps()

    rows = []
    for pkg in pip_names:
        key = pkg.lower()
        imp = PIP_TO_IMPORT.get(key, key.replace("-", "_"))
        used_direct = (imp in imported)
        used_transit = (key in req_by)  # required by someone
        rows.append({
            "pip": pkg,
            "import": imp,
            "used_direct_import": used_direct,
            "used_as_dependency": used_transit,
            "required_by": req_by.get(key, [])[:8],
        })

    # "candidate" = neither direct nor dependency
    candidates = [r for r in rows if (not r["used_direct_import"]) and (not r["used_as_dependency"])]

    print("== PKG USAGE AUDIT (direct + dependency) ==")
    print("counts:")
    print(" - pip_total:", len(rows))
    print(" - direct_import_seen:", sum(1 for r in rows if r["used_direct_import"]))
    print(" - used_as_dependency:", sum(1 for r in rows if r["used_as_dependency"]))
    print(" - candidates(neither):", len(candidates))

    print("\n== candidates (neither direct import nor required) ==")
    for r in candidates:
        print(f" - {r['pip']} (import='{r['import']}')")

    outp = Path.home() / "hpfa" / "_diag" / "pkg_usage_audit.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps({
        "roots": [str(r) for r in ROOTS],
        "rows": rows,
        "candidates": candidates,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n[OK] wrote:", outp)

if __name__ == "__main__":
    main()
