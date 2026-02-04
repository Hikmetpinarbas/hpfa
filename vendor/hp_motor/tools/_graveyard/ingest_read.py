import os
import csv
import pandas as pd

COMMON_DELIMS = [",", ";", "\t", "|"]

def sniff_delimiter(path: str, bytes_to_read: int = 64_000) -> str:
    with open(path, "rb") as f:
        b = f.read(bytes_to_read)
    s = b.decode("utf-8", errors="ignore")
    try:
        d = csv.Sniffer().sniff(s, delimiters="".join(COMMON_DELIMS)).delimiter
        return d
    except Exception:
        # fallback: choose delimiter with max count
        counts = {c: s.count(c) for c in COMMON_DELIMS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","  # last resort

def read_csv_auto(path: str) -> pd.DataFrame:
    delim = sniff_delimiter(path)
    # dtype=str avoids pandas guessing surprises; we'll cast later in schema step
    df = pd.read_csv(path, sep=delim, engine="python", dtype=str)
    if df.shape[1] <= 1:
        raise ValueError(f"CSV parsed into 1 column; likely wrong delimiter. detected={repr(delim)} cols={df.columns.tolist()[:5]}")
    df.attrs["detected_delimiter"] = delim
    return df

def main():
    p = os.path.expanduser("~/hp_motor/data/raw/city_gs.csv")
    df = read_csv_auto(p)
    print("[ingest_read] file:", p)
    print("[ingest_read] detected_delimiter:", repr(df.attrs.get("detected_delimiter")))
    print("[ingest_read] shape:", df.shape)
    print("[ingest_read] columns:", list(df.columns))
    print("\n[ingest_read] head(5):")
    print(df.head(5).to_string(index=False))

if __name__ == "__main__":
    main()
