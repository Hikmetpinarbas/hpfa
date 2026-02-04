import pathlib

def test_motor_bridge_does_not_import_vendor_hp_motor():
    root = pathlib.Path(__file__).resolve().parents[2]
    bridge = root / "motor_bridge"
    assert bridge.exists()

    forbidden = [
        "vendor.hp_motor",
        "vendor/hp_motor",
        "hp_motor",  # direct import also forbidden at this layer
    ]

    for py in bridge.rglob("*.py"):
        txt = py.read_text(encoding="utf-8")
        for f in forbidden:
            assert f not in txt, f"Forbidden reference '{f}' in {py}"
