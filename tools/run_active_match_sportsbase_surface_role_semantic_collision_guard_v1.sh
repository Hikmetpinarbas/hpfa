#!/usr/bin/env bash
set -euo pipefail

CODE="${HPFA_PRODUCT_REPO:?HPFA_PRODUCT_REPO_required}"
RUNTIME="${HPFA_ACTIVE_MATCH:?HPFA_ACTIVE_MATCH_required}"
EXPECTED_RUNTIME="${HPFA_EXPECTED_ACTIVE_MATCH:?HPFA_EXPECTED_ACTIVE_MATCH_required}"
EXPECTED_BRANCH="${HPFA_EXPECTED_BRANCH:?HPFA_EXPECTED_BRANCH_required}"
EXPECTED_HEAD="${HPFA_EXPECTED_HEAD:?HPFA_EXPECTED_HEAD_required}"
PHONE="${HPFA_PHONE_OUTPUT:?HPFA_PHONE_OUTPUT_required}"

fail() {
  echo "FAIL:$1" >&2
  exit 2
}

[ -d "$CODE/.git" ] || fail "PRODUCT_REPO_NOT_GIT:$CODE"
[ -d "$RUNTIME" ] || fail "ACTIVE_MATCH_NOT_FOUND:$RUNTIME"

realpath_py() {
  python - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

CODE_REAL="$(realpath_py "$CODE")"
RUNTIME_REAL="$(realpath_py "$RUNTIME")"
EXPECTED_RUNTIME_REAL="$(realpath_py "$EXPECTED_RUNTIME")"
PHONE_REAL="$(realpath_py "$PHONE")"

[ "$RUNTIME_REAL" = "$EXPECTED_RUNTIME_REAL" ] || fail "RUNTIME_AUTHORITY_MISMATCH:$RUNTIME_REAL"
case "$RUNTIME_REAL" in
  */runtime/active_single_match/current) ;;
  *) fail "RUNTIME_AUTHORITY_PATH_INVALID:$RUNTIME_REAL" ;;
esac

case "$PHONE_REAL" in
  /sdcard/Download/HPFA|/storage/emulated/0/Download/HPFA) ;;
  *) fail "nested_phone_output_directory_rejected" ;;
esac

ACTUAL_BRANCH="$(git -C "$CODE_REAL" symbolic-ref --quiet --short HEAD || true)"
ACTUAL_HEAD="$(git -C "$CODE_REAL" rev-parse HEAD)"
[ "$ACTUAL_BRANCH" = "$EXPECTED_BRANCH" ] || fail "WRONG_BRANCH:$ACTUAL_BRANCH"
[ "$ACTUAL_HEAD" = "$EXPECTED_HEAD" ] || fail "WRONG_HEAD:$ACTUAL_HEAD"

mkdir -p "$PHONE_REAL"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/hpfa-surface-role-collision.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/fresh/semantics" "$WORK/fresh/row" "$WORK/fresh/evidence" "$WORK/fresh/identity" "$WORK/fresh/bundles" "$WORK/bundle"

DISCOVERY="$WORK/runtime_artifact_discovery.json"
python - "$RUNTIME_REAL" "$DISCOVERY" <<'PY'
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
required = [
    "multiformat_file_inventory_lite_v1",
    "csv_surface_reader_lite_v1",
    "xlsx_surface_reader_lite_v1",
    "xml_surface_reader_lite_v1",
    "provider_alias_field_semantics_lite_v1",
    "cross_format_reconciliation_lite_v1",
    "aggregate_definition_alignment_lite_v1",
    "provider_metric_dictionary_lite_v1",
]
by_module: dict[str, list[tuple[Path, str]]] = {key: [] for key in required}
registry_candidates: list[tuple[Path, str]] = []

for path in root.rglob("*.json"):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not isinstance(payload, dict):
        continue
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    module_id = payload.get("module_id")
    if module_id in by_module:
        by_module[module_id].append((path, digest))
    rules = payload.get("exact_group_rules")
    if payload.get("candidate_only") is True and isinstance(rules, list) and rules:
        required_keys = {"action", "period", "team", "pos_x", "pos_y"}
        found = {str(row.get("field_key_candidate")) for row in rules if isinstance(row, dict)}
        if required_keys.issubset(found):
            registry_candidates.append((path, digest))

def resolve(name: str, rows: list[tuple[Path, str]]) -> dict[str, object]:
    if not rows:
        raise SystemExit(f"FAIL:runtime_artifact_missing:{name}")
    hashes = {digest for _, digest in rows}
    if len(hashes) != 1:
        detail = ",".join(str(path.relative_to(root)) for path, _ in sorted(rows))
        raise SystemExit(f"FAIL:runtime_artifact_divergent:{name}:{detail}")
    chosen = sorted(rows, key=lambda item: (len(item[0].parts), str(item[0])))[0][0]
    return {
        "path": str(chosen),
        "duplicate_reflection_count": len(rows) - 1,
        "payload_sha256": next(iter(hashes)),
    }

resolved = {key: resolve(key, value) for key, value in by_module.items()}
resolved["xml_group_registry"] = resolve("xml_group_registry", registry_candidates)
out.write_text(json.dumps({"runtime_authority": str(root), "artifacts": resolved}, indent=2, sort_keys=True), encoding="utf-8")
PY

artifact_path() {
  python - "$DISCOVERY" "$1" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding="utf-8"))
print(p["artifacts"][sys.argv[2]]["path"])
PY
}

INVENTORY="$(artifact_path multiformat_file_inventory_lite_v1)"
CSV="$(artifact_path csv_surface_reader_lite_v1)"
XLSX="$(artifact_path xlsx_surface_reader_lite_v1)"
XML="$(artifact_path xml_surface_reader_lite_v1)"
FIELD="$(artifact_path provider_alias_field_semantics_lite_v1)"
RECON="$(artifact_path cross_format_reconciliation_lite_v1)"
AGG="$(artifact_path aggregate_definition_alignment_lite_v1)"
METRIC="$(artifact_path provider_metric_dictionary_lite_v1)"
XML_GROUP="$(artifact_path xml_group_registry)"
REGISTRY="$CODE_REAL/hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json"

export PYTHONPATH="$CODE_REAL${PYTHONPATH:+:$PYTHONPATH}"

python "$CODE_REAL/hpfa/modules/core/provider_label_value_semantics_lite/src/provider_label_value_semantics.py" \
  --runtime-root "$RUNTIME_REAL" \
  --expected-active-match "$EXPECTED_RUNTIME_REAL" \
  --csv "$CSV" \
  --xlsx "$XLSX" \
  --xml "$XML" \
  --field-semantics "$FIELD" \
  --registry "$REGISTRY" \
  --out "$WORK/fresh/semantics" \
  >"$WORK/provider_semantics_stdout.txt" 2>&1

SEM="$WORK/fresh/semantics/provider_label_value_semantics_lite_v1.json"

python "$CODE_REAL/hpfa/modules/core/row_nucleus_inventory_lite/src/row_nucleus_inventory_hardened.py" \
  --input-root "$RUNTIME_REAL" \
  --inventory "$INVENTORY" \
  --csv-audit "$CSV" \
  --xml-audit "$XML" \
  --field-semantics "$FIELD" \
  --label-semantics "$SEM" \
  --reconciliation "$RECON" \
  --aggregate-alignment "$AGG" \
  --metric-dictionary "$METRIC" \
  --xml-group-registry "$XML_GROUP" \
  --out "$WORK/fresh/row" \
  >"$WORK/row_nucleus_stdout.txt" 2>&1

ROW="$WORK/fresh/row/row_nucleus_inventory_lite_v1.json"

python "$CODE_REAL/hpfa/modules/core/evidence_atom_inventory_lite/src/evidence_atom_inventory.py" \
  --row-nucleus "$ROW" \
  --out "$WORK/fresh/evidence" \
  >"$WORK/evidence_atom_stdout.txt" 2>&1

EVIDENCE="$WORK/fresh/evidence/evidence_atom_inventory_lite_v1.json"

python "$CODE_REAL/hpfa/modules/core/match_local_identity_candidates_lite/src/match_local_identity_candidates.py" \
  --evidence "$EVIDENCE" \
  --out "$WORK/fresh/identity" \
  >"$WORK/match_local_identity_stdout.txt" 2>&1

IDENTITY="$WORK/fresh/identity/match_local_identity_candidates_lite_v1.json"

python "$CODE_REAL/hpfa/modules/core/semantic_role_action_bundle_candidates_lite/src/semantic_role_action_bundle_candidates.py" \
  --evidence "$EVIDENCE" \
  --identity "$IDENTITY" \
  --out "$WORK/fresh/bundles" \
  >"$WORK/action_bundle_stdout.txt" 2>&1

BUNDLES="$WORK/fresh/bundles/semantic_role_action_bundle_candidates_lite_v1.json"
VERIFY_JSON="$WORK/bundle/sportsbase_surface_role_semantic_collision_guard_active_match_v1.json"
VERIFY_TXT="$WORK/bundle/sportsbase_surface_role_semantic_collision_guard_active_match_v1.txt"

python - "$SEM" "$ROW" "$EVIDENCE" "$IDENTITY" "$BUNDLES" "$VERIFY_JSON" "$VERIFY_TXT" "$ACTUAL_BRANCH" "$ACTUAL_HEAD" "$RUNTIME_REAL" <<'PY'
from __future__ import annotations
import json, sys
from pathlib import Path

sem_p, row_p, ev_p, id_p, bundle_p, out_json, out_txt, branch, head, runtime = sys.argv[1:]
sem=json.load(open(sem_p, encoding="utf-8"))
row=json.load(open(row_p, encoding="utf-8"))
ev=json.load(open(ev_p, encoding="utf-8"))
ident=json.load(open(id_p, encoding="utf-8"))
bundles=json.load(open(bundle_p, encoding="utf-8"))

affected={
    "Goal kicks short (0-15 m)",
    "Goal kicks medium (15-40 m)",
    "Goal kicks long (40+ m)",
}
all_goal_kick_labels=affected | {"Goal kicks"}

team_sem=[r for r in sem.get("provider_label_records", []) if r.get("source_role")=="TEAM_SURFACE_CANDIDATE" and r.get("raw_label") in affected]
team_sem_ok=[r for r in team_sem if r.get("semantic_role_candidate")=="ATTRIBUTE_REFERENCE" and r.get("action_family_candidate")=="PASS" and r.get("restart_type_candidate") in {None, ""} and r.get("downstream_eligibility")=="REFERENCE_ONLY" and r.get("semantics_decision")=="CONTEXT_DEPENDENT_SEMANTIC_COLLISION"]

team_ref_atoms=[a for a in ev.get("evidence_atoms", []) if a.get("source_role")=="TEAM_SURFACE_CANDIDATE" and a.get("raw_label") in affected and a.get("semantic_role_candidate")=="ATTRIBUTE_REFERENCE" and a.get("atom_class")=="REFERENCE_ATOM"]

gk_goal_kick_atoms=[a for a in ev.get("evidence_atoms", []) if a.get("source_role")=="GOALKEEPER_SURFACE_CANDIDATE" and a.get("raw_label") in all_goal_kick_labels and a.get("semantic_role_candidate")=="ACTION_ANCHOR" and a.get("atom_class")=="ACTION_ANCHOR_ATOM" and "RESTART" in (a.get("action_family_candidates") or [])]

team_contaminated_bundles=[b for b in bundles.get("action_bundle_candidates", []) if b.get("source_role")=="TEAM_SURFACE_CANDIDATE" and b.get("action_family_candidate")=="RESTART" and bool(set(b.get("raw_labels") or []) & affected)]

team_any_affected_bundles=[b for b in bundles.get("action_bundle_candidates", []) if b.get("source_role")=="TEAM_SURFACE_CANDIDATE" and bool(set(b.get("raw_labels") or []) & affected)]

team_ref_routes=[]
atom_ids={a.get("evidence_atom_id") for a in team_ref_atoms}
for route in bundles.get("semantic_route_records", []):
    if route.get("evidence_atom_id") in atom_ids and route.get("semantic_route")=="REFERENCE_ROUTE":
        team_ref_routes.append(route)

claims_ok=True
claim_rows={}
for name,payload in (("semantics",sem),("row_nucleus",row),("evidence_atom",ev),("identity",ident),("action_bundles",bundles)):
    c=payload.get("canonical_event_count")
    pr=payload.get("production_release")
    good=(c=="UNKNOWN" and pr is False)
    claim_rows[name]={"canonical_event_count":c,"production_release":pr,"ok":good}
    claims_ok &= good

checks={
    "team_surface_three_exact_semantic_records_present": len(team_sem)==3,
    "team_surface_semantics_collision_contract_pass": len(team_sem_ok)==3,
    "team_goal_kick_length_reference_atoms_preserved": len(team_ref_atoms)>0,
    "team_goal_kick_length_reference_routes_preserved": len(team_ref_routes)==len(team_ref_atoms) and len(team_ref_atoms)>0,
    "team_goal_kick_length_restart_action_bundle_count_zero": len(team_contaminated_bundles)==0,
    "team_goal_kick_length_any_action_bundle_count_zero": len(team_any_affected_bundles)==0,
    "goalkeeper_goal_kick_action_anchor_evidence_preserved": len(gk_goal_kick_atoms)>0,
    "claim_boundaries_preserved": claims_ok,
}
status="ACTIVE_MATCH_EVIDENCE_PASS" if all(checks.values()) else "FAIL_CLOSED"
result={
    "module_id":"sportsbase_surface_role_semantic_collision_guard_active_match_v1",
    "status":status,
    "runtime_evidence_status":status,
    "runtime_authority":runtime,
    "runtime_branch":branch,
    "runtime_code_head_sha":head,
    "checks":checks,
    "counts":{
        "team_surface_semantic_records":len(team_sem),
        "team_surface_semantic_records_contract_ok":len(team_sem_ok),
        "team_goal_kick_length_reference_atom_count":len(team_ref_atoms),
        "team_goal_kick_length_reference_route_count":len(team_ref_routes),
        "team_goal_kick_length_restart_action_bundle_count":len(team_contaminated_bundles),
        "team_goal_kick_length_any_action_bundle_count":len(team_any_affected_bundles),
        "goalkeeper_goal_kick_action_anchor_atom_count":len(gk_goal_kick_atoms),
        "fresh_action_bundle_candidate_count":bundles.get("action_bundle_candidate_count"),
        "fresh_restart_action_bundle_count":(bundles.get("action_bundle_family_counts") or {}).get("RESTART",0),
    },
    "claim_boundary_audit":claim_rows,
    "validated_provider_semantics":False,
    "validated_provider_goal_kick_definition":False,
    "pass_distance_truth":False,
    "canonical_event_count":"UNKNOWN",
    "progression_truth":False,
    "line_break_truth":False,
    "tactical_truth":False,
    "production_release":False,
}
Path(out_json).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
lines=[
    "HPFA SPORTSBASE SURFACE-ROLE SEMANTIC COLLISION GUARD — ACTIVE_MATCH V1",
    f"status={status}",
    f"runtime_authority={runtime}",
    f"runtime_branch={branch}",
    f"runtime_code_head_sha={head}",
]
lines += [f"{k}={str(v).lower() if isinstance(v,bool) else v}" for k,v in checks.items()]
lines += [f"{k}={v}" for k,v in result["counts"].items()]
lines += [
    "canonical_event_count=UNKNOWN",
    "validated_provider_semantics=false",
    "validated_provider_goal_kick_definition=false",
    "pass_distance_truth=false",
    "progression_truth=false",
    "line_break_truth=false",
    "tactical_truth=false",
    "production_release=false",
]
Path(out_txt).write_text("\n".join(lines)+"\n",encoding="utf-8")
if status != "ACTIVE_MATCH_EVIDENCE_PASS":
    raise SystemExit(2)
PY

python -m pytest -q "$CODE_REAL/tools/tests/test_sportsbase_surface_role_semantic_collision_guard_v1.py" \
  >"$WORK/bundle/sportsbase_surface_role_semantic_collision_guard_pytest_v1.txt" 2>&1

cp "$DISCOVERY" "$WORK/bundle/runtime_artifact_discovery_v1.json"
cp "$SEM" "$WORK/bundle/provider_label_value_semantics_lite_v1.json"
cp "$ROW" "$WORK/bundle/row_nucleus_inventory_lite_v1.json"
cp "$EVIDENCE" "$WORK/bundle/evidence_atom_inventory_lite_v1.json"
cp "$IDENTITY" "$WORK/bundle/match_local_identity_candidates_lite_v1.json"
cp "$BUNDLES" "$WORK/bundle/semantic_role_action_bundle_candidates_lite_v1.json"
cp "$WORK/provider_semantics_stdout.txt" "$WORK/bundle/provider_semantics_stdout_v1.txt"
cp "$WORK/row_nucleus_stdout.txt" "$WORK/bundle/row_nucleus_stdout_v1.txt"
cp "$WORK/evidence_atom_stdout.txt" "$WORK/bundle/evidence_atom_stdout_v1.txt"
cp "$WORK/match_local_identity_stdout.txt" "$WORK/bundle/match_local_identity_stdout_v1.txt"
cp "$WORK/action_bundle_stdout.txt" "$WORK/bundle/action_bundle_stdout_v1.txt"

python - "$WORK/bundle" <<'PY'
import hashlib, json, sys
from pathlib import Path
root=Path(sys.argv[1])
rows=[]
for path in sorted(root.iterdir()):
    if path.name=="manifest_sha256_v1.json" or not path.is_file():
        continue
    rows.append({"file":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"size":path.stat().st_size})
(root/"manifest_sha256_v1.json").write_text(json.dumps({"files":rows},indent=2,sort_keys=True),encoding="utf-8")
PY

ZIP="$PHONE_REAL/sportsbase_surface_role_semantic_collision_guard_active_match_bundle_v1.zip"
rm -f "$ZIP"
python - "$WORK/bundle" "$ZIP" <<'PY'
import sys, zipfile
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2])
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(root.iterdir()):
        if path.is_file():
            zf.write(path, arcname=path.name)
PY

python - "$ZIP" <<'PY'
import sys, zipfile
p=sys.argv[1]
with zipfile.ZipFile(p) as zf:
    bad=zf.testzip()
    if bad:
        raise SystemExit(f"FAIL:ZIP_CRC:{bad}")
    print(f"ZIP_OK={p}")
    print(f"ZIP_FILE_COUNT={len(zf.infolist())}")
PY

echo "PRODUCT_CODE_OK=$CODE_REAL"
echo "ACTIVE_MATCH_OK=$RUNTIME_REAL"
echo "BRANCH_OK=$ACTUAL_BRANCH"
echo "HEAD_OK=$ACTUAL_HEAD"
echo "OUTPUT=$ZIP"
