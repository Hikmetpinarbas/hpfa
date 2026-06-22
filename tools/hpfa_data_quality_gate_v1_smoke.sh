#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKDIR="${TMPDIR:-/tmp}/hpfa_dqg_smoke"
SCRIPT="$ROOT/tools/hpfa_data_quality_gate_v1.py"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR" "$WORKDIR/archive_sample"

cat > "$WORKDIR/events.csv" <<'CSV'
id,action,team_id,half,minute,x,y
1,pass,home,1,1,10,20
2,pass,away,1,2,30,40
3,shot,home,1,3,90,50
CSV

python "$SCRIPT" "$WORKDIR/events.csv" \
  --out "$WORKDIR/gate_report.json" \
  --summary-out "$WORKDIR/gate_summary.txt"

python - "$WORKDIR/gate_report.json" <<'PY'
import json, sys
p=sys.argv[1]
with open(p, encoding='utf-8') as f:
    data=json.load(f)
assert data['status']=='PASS', data
assert data['claim_safety']=='NO_FOOTBALL_CLAIMS_EMITTED', data
assert data['next_action']['phase_sequence_allowed'] is True, data
assert data['next_action']['metric_layer_allowed'] is True, data
assert data['next_action']['claim_layer_allowed'] is False, data
assert data['valid_row_count']==3, data
assert data['findings'], data
PY

cp "$WORKDIR/events.csv" "$WORKDIR/archive_sample/events.csv"
python "$SCRIPT" "$WORKDIR/archive_sample/events.csv" \
  --out "$WORKDIR/archive_gate_report.json" \
  --summary-out "$WORKDIR/archive_gate_summary.txt"

python - "$WORKDIR/archive_gate_report.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data=json.load(f)
assert data['status']=='FAIL_CLOSED', data
assert data['next_action']['phase_sequence_allowed'] is False, data
assert data['next_action']['metric_layer_allowed'] is False, data
assert data['next_action']['claim_layer_allowed'] is False, data
PY

cat > "$WORKDIR/no_coordinates.csv" <<'CSV'
id,action,team_id,half,minute
1,pass,home,1,1
2,pass,away,1,2
CSV
python "$SCRIPT" "$WORKDIR/no_coordinates.csv" \
  --out "$WORKDIR/no_coordinates_gate_report.json" \
  --summary-out "$WORKDIR/no_coordinates_gate_summary.txt"

python - "$WORKDIR/no_coordinates_gate_report.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data=json.load(f)
assert data['status']=='DEGRADED', data
assert data['next_action']['phase_sequence_allowed'] is True, data
assert data['next_action']['metric_layer_allowed']=='CONDITIONAL', data
assert data['next_action']['claim_layer_allowed'] is False, data
PY

cat > "$WORKDIR/bad.jsonl" <<'JSONL'
{"id":"1","action":"pass","team_id":"home","half":1,"minute":1,"x":10,"y":20}
{bad json
JSONL
python "$SCRIPT" "$WORKDIR/bad.jsonl" \
  --out "$WORKDIR/bad_jsonl_gate_report.json" \
  --summary-out "$WORKDIR/bad_jsonl_gate_summary.txt"

python - "$WORKDIR/bad_jsonl_gate_report.json" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    data=json.load(f)
assert data['status']=='FAIL_CLOSED', data
ids=[f['gate_id'] for f in data['findings']]
assert 'G00_PARSE' in ids, data
PY

echo "HPFA_DQG_SMOKE_PASS"
echo "WORKDIR=$WORKDIR"
