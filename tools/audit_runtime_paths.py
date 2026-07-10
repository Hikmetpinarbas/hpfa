import importlib
import site
import subprocess
import sys
from pathlib import Path


def show(title, items):
    print(f"\n== {title} ==")
    for item in items:
        print(item)


def pip_show(package_name: str) -> None:
    print(f"\n== pip show {package_name} ==")
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "show", package_name],
        check=False,
        text=True,
        capture_output=True,
        timeout=30,
    )
    output = completed.stdout if completed.stdout else completed.stderr
    for line in output.splitlines()[:120]:
        print(line)
    if completed.returncode not in {0, 1}:
        print(f"pip_show_failed:returncode={completed.returncode}")


print("python:", sys.executable)
print("prefix:", sys.prefix)
print("base_prefix:", sys.base_prefix)

show("sys.path (head)", sys.path[:30])

site_packages = []
try:
    site_packages = site.getsitepackages()
except Exception:
    pass
show("site-packages", site_packages)

pth_files = []
for package_path in site_packages:
    directory = Path(package_path)
    if directory.exists():
        pth_files += sorted(directory.glob("*.pth"))
show(".pth files", [str(path) for path in pth_files])

for target in ["hpfa", "hp_motor"]:
    try:
        module = importlib.import_module(target)
        print(f"\n== import {target} ==")
        print("module:", module)
        print("__file__:", getattr(module, "__file__", None))
        print("__path__:", list(getattr(module, "__path__", [])) if hasattr(module, "__path__") else None)
        print("__spec__:", getattr(module, "__spec__", None))
    except Exception as exc:
        print(f"\n== import {target} FAIL == {exc}")

pip_show("hp-motor")
pip_show("hpfa")
