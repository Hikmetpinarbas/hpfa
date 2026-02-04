import json
from pathlib import Path

INDEX_PATH = Path("artifacts/reports/index_reports.json")

def main():
    if not INDEX_PATH.exists():
        print(f"ERR: missing {INDEX_PATH}")
        raise SystemExit(2)

    data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    t = type(data).__name__
    print(f"OK: index type={t}")

    if isinstance(data, dict):
        keys = list(data.keys())
        print(f"OK: dict keys sample={keys[:10]}")
        # try to locate records container
        for k in ["reports", "items", "data", "index", "records"]:
            if k in data and isinstance(data[k], list):
                print(f"OK: records found at key='{k}', n={len(data[k])}")
                if data[k]:
                    print(f"OK: first record keys={sorted(list(data[k][0].keys()))[:30]}")
                return
        print("WARN: dict index but no obvious records list key found")
        return

    if isinstance(data, list):
        print(f"OK: list n={len(data)}")
        if data:
            print(f"OK: first record keys={sorted(list(data[0].keys()))[:30]}")
        return

    print("ERR: unsupported index root type")
    raise SystemExit(3)

if __name__ == "__main__":
    main()
