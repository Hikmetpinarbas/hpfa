import sys, site, os
from pathlib import Path
import importlib

def show(title, items):
    print(f"\n== {title} ==")
    for x in items:
        print(x)

print("python:", sys.executable)
print("prefix:", sys.prefix)
print("base_prefix:", sys.base_prefix)

# sys.path
show("sys.path (head)", sys.path[:30])

# site-packages + .pth files
sp = []
try:
    sp = site.getsitepackages()
except Exception:
    pass
show("site-packages", sp)

pths = []
for p in sp:
    d = Path(p)
    if d.exists():
        pths += sorted(d.glob("*.pth"))
show(".pth files", [str(p) for p in pths])

# import targets
targets = ["hpfa", "hp_motor"]
for t in targets:
    try:
        m = importlib.import_module(t)
        print(f"\n== import {t} ==")
        print("module:", m)
        print("__file__:", getattr(m, "__file__", None))
        print("__path__:", list(getattr(m, "__path__", [])) if hasattr(m, "__path__") else None)
        print("__spec__:", getattr(m, "__spec__", None))
    except Exception as e:
        print(f"\n== import {t} FAIL == {e}")

# pip editable check
print("\n== pip show hp-motor ==")
os.system("python -m pip show hp-motor | sed -n '1,120p'")

print("\n== pip show hpfa ==")
os.system("python -m pip show hpfa | sed -n '1,120p'")
