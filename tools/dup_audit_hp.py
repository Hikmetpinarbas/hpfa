import os
from pathlib import Path

HOME = Path.home()

TARGETS = [
    ("hp_motor", "hp_motor"),
    ("hpfa", "hpfa"),
]

def is_pkg_dir(d: Path) -> bool:
    return (d / "__init__.py").exists()

def main():
    print("HOME:", HOME)
    print("== DUP AUDIT ==")

    for label, pkg in TARGETS:
        print(f"\n## {label} ##")
        # hem paket klasörü, hem repo kökü olabilecek adaylar
        dirs = sorted({p.parent for p in HOME.rglob(pkg) if p.is_dir()})
        if not dirs:
            print(" - none found")
            continue

        for d in dirs:
            pkgdir = d / pkg
            mark = []
            if pkgdir.exists() and pkgdir.is_dir():
                mark.append("pkgdir")
                if is_pkg_dir(pkgdir):
                    mark.append("init")
            # repo kökü sinyalleri
            if (d / "pyproject.toml").exists():
                mark.append("pyproject")
            if (d / "setup.py").exists() or (d / "setup.cfg").exists():
                mark.append("setup")
            print(f" - {d}  [{' '.join(mark) if mark else 'no-mark'}]")

if __name__ == "__main__":
    main()
