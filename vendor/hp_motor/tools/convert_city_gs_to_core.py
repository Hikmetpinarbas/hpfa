import os
import re
import csv
import math
import pandas as pd

COMMON_DELIMS = [",", ";", "\t", "|"]

CORE_COLS = [
    "event_id",
    "t_start",
    "t_end",
    "half",
    "team_name",
    "team_id",
    "player_name",
    "player_id",
    "event_code_raw",
    "action_raw",
    "action_label",
    "pos_x",
    "pos_y",
]

def sniff_delimiter(path: str, bytes_to_read: int = 64_000) -> str:
    with open(path, "rb") as f:
        b = f.read(bytes_to_read)
    s = b.decode("utf-8", errors="ignore")
    try:
        return csv.Sniffer().sniff(s, delimiters="".join(COMMON_DELIMS)).delimiter
    except Exception:
        counts = {c: s.count(c) for c in COMMON_DELIMS}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ","

def read_csv_auto(path: str) -> pd.DataFrame:
    delim = sniff_delimiter(path)
    df = pd.read_csv(path, sep=delim, engine="python", dtype=str)
    if df.shape[1] <= 1:
        raise ValueError(f"CSV parsed into 1 column; detected={repr(delim)}")
    df.attrs["detected_delimiter"] = delim
    return df

TEAM_RE = re.compile(r"^(?P<name>.*?)(?:\s*\((?P<id>\d+)\))?\s*$")
CODE_RE = re.compile(r"^\s*(?P<num>\d+)\.\s*(?P<player>.+?)\s*\((?P<pid>\d+)\)\s*-\s*(?P<label>.+?)\s*$")

def is_nan(x) -> bool:
    try:
        return isinstance(x, float) and math.isnan(x)
    except Exception:
        return False

def clean_str(x) -> str:
    if x is None or is_nan(x):
        return ""
    s = str(x).strip()
    if s.lower() == "nan":
        return ""
    return s

def parse_team(s):
    s = clean_str(s)
    if not s:
        return None, None
    m = TEAM_RE.match(s)
    if not m:
        return s, None
    name = (m.group("name") or "").strip() or None
    tid = m.group("id")
    return name, int(tid) if tid else None

def parse_code(s):
    s = clean_str(s)
    if not s:
        return None, None, None
    m = CODE_RE.match(s)
    if not m:
        return None, None, None
    player = m.group("player").strip()
    pid = int(m.group("pid"))
    label = m.group("label").strip()
    return player, pid, label

def to_float(x):
    s = clean_str(x)
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None

def to_int(x):
    s = clean_str(x)
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def normalize_action_label(code_label, action_raw):
    base = clean_str(code_label)
    if not base:
        base = clean_str(action_raw)
    if not base:
        return None
    base = re.sub(r"\s+", " ", base).strip().lower()
    return base

def main():
    src = os.path.expanduser("~/hp_motor/data/raw/city_gs.csv")
    out = os.path.expanduser("~/hp_motor/data/processed/city_gs_events_core.csv")

    df = read_csv_auto(src)

    required = {"ID","start","end","code","team","action","half","pos_x","pos_y"}
    missing = sorted([c for c in required if c not in df.columns])
    if missing:
        raise KeyError(f"Missing required columns: {missing}. Have: {list(df.columns)}")

    team_parsed = df["team"].apply(parse_team)
    df["team_name"] = team_parsed.apply(lambda t: t[0])
    df["team_id"] = team_parsed.apply(lambda t: t[1])

    code_parsed = df["code"].apply(parse_code)
    df["player_name"] = code_parsed.apply(lambda t: t[0])
    df["player_id"] = code_parsed.apply(lambda t: t[1])
    df["code_label"] = code_parsed.apply(lambda t: t[2])

    core = pd.DataFrame()
    core["event_id"] = df["ID"].apply(to_int)
    core["t_start"] = df["start"].apply(to_float)
    core["t_end"] = df["end"].apply(to_float)
    core["half"] = df["half"].apply(to_int)
    core["team_name"] = df["team_name"]
    core["team_id"] = df["team_id"]
    core["player_name"] = df["player_name"]
    core["player_id"] = df["player_id"]
    core["event_code_raw"] = df["code"]
    core["action_raw"] = df["action"]
    core["action_label"] = [
        normalize_action_label(a, b) for a, b in zip(df["code_label"].tolist(), df["action"].tolist())
    ]
    core["pos_x"] = df["pos_x"].apply(to_float)
    core["pos_y"] = df["pos_y"].apply(to_float)

    core = core[CORE_COLS]
    core.to_csv(out, index=False)

    print("[convert_core] src:", src)
    print("[convert_core] detected_delimiter:", repr(df.attrs.get("detected_delimiter")))
    print("[convert_core] out:", out)
    print("[convert_core] shape:", core.shape)
    print("[convert_core] null_team_name:", int(core["team_name"].isna().sum()))
    print("[convert_core] null_player_id:", int(core["player_id"].isna().sum()))
    print("[convert_core] unique_action_label:", int(core["action_label"].nunique(dropna=True)))
    print("\n[convert_core] head(8):")
    print(core.head(8).to_string(index=False))

if __name__ == "__main__":
    main()
