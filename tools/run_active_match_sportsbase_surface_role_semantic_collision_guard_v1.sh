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

realpath_py() {
  python - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

[ -d "$CODE/.git" ] || fail "PRODUCT_REPO_NOT_GIT:$CODE"
[ -d "$RUNTIME" ] || fail "ACTIVE_MATCH_NOT_FOUND:$RUNTIME"

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
[ -z "$(git -C "$CODE_REAL" status --porcelain --untracked-files=no)" ] || fail "TRACKED_WORKTREE_NOT_CLEAN:$CODE_REAL"

mkdir -p "$PHONE_REAL"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/hpfa-surface-role-collision.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p \
  "$WORK/fresh/inventory" \
  "$WORK/fresh/csv" \
  "$WORK/fresh/xlsx" \
  "$WORK/fresh/xml" \
  "$WORK/fresh/field" \
  "$WORK/fresh/semantics" \
  "$WORK/fresh/reconciliation" \
  "$WORK/fresh/metric" \
  "$WORK/fresh/aggregate" \
  "$WORK/fresh/row" \
  "$WORK/fresh/evidence" \
  "$WORK/fresh/identity" \
  "$WORK/fresh/bundles" \
  "$WORK/logs" \
  "$WORK/bundle"

export PYTHONPATH="$CODE_REAL${PYTHONPATH:+:$PYTHONPATH}"
cd "$CODE_REAL"

run_stage() {
  local name="$1"
  shift
  local log="$WORK/logs/${name}.txt"
  echo "STAGE_START=$name"
  set +e
  "$@" >"$log" 2>&1
  local rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    echo "STAGE_FAIL=$name rc=$rc" >&2
    cat "$log" >&2 || true
    fail "stage_failed:$name:rc=$rc"
  fi
  echo "STAGE_PASS=$name"
}

# Fresh upstream production from raw ACTIVE_MATCH. No runtime-discovered or phone-stored
# derived JSON is consumed by this runner.
run_stage inventory \
  python "$CODE_REAL/multiformat_file_inventory.py" \
    --input-root "$RUNTIME_REAL" \
    --runtime-authority "$EXPECTED_RUNTIME_REAL" \
    --active-match-execution \
    --out "$WORK/fresh/inventory"

INVENTORY="$WORK/fresh/inventory/multiformat_file_inventory_lite_v1.json"
[ -f "$INVENTORY" ] || fail "fresh_inventory_output_missing"

run_stage csv_surface \
  python "$CODE_REAL/csv_surface_reader_lite.py" \
    --input-root "$RUNTIME_REAL" \
    --inventory "$INVENTORY" \
    --out "$WORK/fresh/csv"
CSV="$WORK/fresh/csv/csv_surface_audit_lite_v1.json"
[ -f "$CSV" ] || fail "fresh_csv_output_missing"

run_stage xlsx_surface \
  python "$CODE_REAL/xlsx_surface_reader_lite.py" \
    --input-root "$RUNTIME_REAL" \
    --inventory "$INVENTORY" \
    --out "$WORK/fresh/xlsx"
XLSX="$WORK/fresh/xlsx/xlsx_surface_audit_lite_v1.json"
[ -f "$XLSX" ] || fail "fresh_xlsx_output_missing"

run_stage xml_surface \
  python "$CODE_REAL/hpfa/modules/core/xml_surface_reader_lite/src/xml_surface_reader.py" \
    --input-root "$RUNTIME_REAL" \
    --inventory "$INVENTORY" \
    --out "$WORK/fresh/xml"
XML="$WORK/fresh/xml/xml_surface_audit_lite_v1.json"
[ -f "$XML" ] || fail "fresh_xml_output_missing"

run_stage field_semantics \
  python "$CODE_REAL/hpfa/modules/core/provider_alias_field_semantics_lite/src/provider_alias_field_semantics.py" \
    --input-root "$RUNTIME_REAL" \
    --csv-audit "$CSV" \
    --xlsx-audit "$XLSX" \
    --xml-audit "$XML" \
    --out "$WORK/fresh/field"
FIELD="$WORK/fresh/field/provider_alias_field_semantics_lite_v1.json"
[ -f "$FIELD" ] || fail "fresh_field_semantics_output_missing"

LABEL_REGISTRY="$CODE_REAL/hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json"
XML_GROUP_REGISTRY="$CODE_REAL/hpfa/modules/core/cross_format_reconciliation_lite/registry/sportsbase_xml_group_semantics_v1.json"
AGGREGATE_REGISTRY="$CODE_REAL/hpfa/modules/core/aggregate_definition_alignment_lite/registry/sportsbase_aggregate_definition_candidates_v1.json"
METRIC_CONFIG="$CODE_REAL/configs/metrics"
for required in "$LABEL_REGISTRY" "$XML_GROUP_REGISTRY" "$AGGREGATE_REGISTRY"; do
  [ -f "$required" ] || fail "product_registry_missing:$required"
done
[ -d "$METRIC_CONFIG" ] || fail "metric_config_directory_missing:$METRIC_CONFIG"

run_stage label_semantics \
  python "$CODE_REAL/hpfa/modules/core/provider_label_value_semantics_lite/src/provider_label_value_semantics.py" \
    --runtime-root "$RUNTIME_REAL" \
    --expected-active-match "$EXPECTED_RUNTIME_REAL" \
    --csv "$CSV" \
    --xlsx "$XLSX" \
    --xml "$XML" \
    --field-semantics "$FIELD" \
    --registry "$LABEL_REGISTRY" \
    --out "$WORK/fresh/semantics"
SEM="$WORK/fresh/semantics/provider_label_value_semantics_lite_v1.json"
[ -f "$SEM" ] || fail "fresh_label_semantics_output_missing"

run_stage reconciliation \
  python "$CODE_REAL/hpfa/modules/core/cross_format_reconciliation_lite/src/cross_format_reconciliation.py" \
    --input-root "$RUNTIME_REAL" \
    --expected-runtime-authority "$EXPECTED_RUNTIME_REAL" \
    --inventory "$INVENTORY" \
    --csv-audit "$CSV" \
    --xlsx-audit "$XLSX" \
    --xml-audit "$XML" \
    --field-semantics "$FIELD" \
    --label-semantics "$SEM" \
    --xml-group-registry "$XML_GROUP_REGISTRY" \
    --out "$WORK/fresh/reconciliation"
RECON="$WORK/fresh/reconciliation/cross_format_reconciliation_lite_v1.json"
[ -f "$RECON" ] || fail "fresh_reconciliation_output_missing"

run_stage metric_dictionary \
  python - "$METRIC_CONFIG" "$WORK/fresh/metric/provider_metric_dictionary_lite_v1.json" <<'PY'
import json, sys
from pathlib import Path
from hpfa.modules.core.provider_metric_dictionary_lite.src.provider_metric_dictionary import load_dictionary_pack
payload = load_dictionary_pack(sys.argv[1])
out = Path(sys.argv[2])
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
if payload.get("status") == "FAIL_CLOSED":
    raise SystemExit(2)
PY
METRIC="$WORK/fresh/metric/provider_metric_dictionary_lite_v1.json"
[ -f "$METRIC" ] || fail "fresh_metric_dictionary_output_missing"

AGG="$WORK/fresh/aggregate/aggregate_definition_alignment_lite_v1.json"
run_stage aggregate_alignment \
  python "$CODE_REAL/aggregate_definition_alignment_lite.py" \
    --xlsx-audit "$XLSX" \
    --label-semantics "$SEM" \
    --metric-config-dir "$METRIC_CONFIG" \
    --registry "$AGGREGATE_REGISTRY" \
    --output "$AGG"
[ -f "$AGG" ] || fail "fresh_aggregate_alignment_output_missing"

run_stage row_nucleus \
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
    --xml-group-registry "$XML_GROUP_REGISTRY" \
    --out "$WORK/fresh/row"
ROW="$WORK/fresh/row/row_nucleus_inventory_lite_v1.json"
[ -f "$ROW" ] || fail "fresh_row_nucleus_output_missing"

run_stage evidence_atoms \
  python "$CODE_REAL/hpfa/modules/core/evidence_atom_inventory_lite/src/evidence_atom_inventory.py" \
    --row-nucleus "$ROW" \
    --out "$WORK/fresh/evidence"
EVIDENCE="$WORK/fresh/evidence/evidence_atom_inventory_lite_v1.json"
[ -f "$EVIDENCE" ] || fail "fresh_evidence_atom_output_missing"

run_stage match_local_identity \
  python "$CODE_REAL/hpfa/modules/core/match_local_identity_candidates_lite/src/match_local_identity_candidates.py" \
    --evidence "$EVIDENCE" \
    --out "$WORK/fresh/identity"
IDENTITY="$WORK/fresh/identity/match_local_identity_candidates_lite_v1.json"
[ -f "$IDENTITY" ] || fail "fresh_identity_output_missing"

run_stage action_bundles \
  python "$CODE_REAL/hpfa/modules/core/semantic_role_action_bundle_candidates_lite/src/semantic_role_action_bundle_candidates.py" \
    --evidence "$EVIDENCE" \
    --identity "$IDENTITY" \
    --out "$WORK/fresh/bundles"
BUNDLES="$WORK/fresh/bundles/semantic_role_action_bundle_candidates_lite_v1.json"
[ -f "$BUNDLES" ] || fail "fresh_action_bundle_output_missing"

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

run_stage focused_tests \
  python -m pytest -q "$CODE_REAL/tools/tests/test_sportsbase_surface_role_semantic_collision_guard_v1.py"

cp "$INVENTORY" "$WORK/bundle/multiformat_file_inventory_lite_v1.json"
cp "$CSV" "$WORK/bundle/csv_surface_audit_lite_v1.json"
cp "$XLSX" "$WORK/bundle/xlsx_surface_audit_lite_v1.json"
cp "$XML" "$WORK/bundle/xml_surface_audit_lite_v1.json"
cp "$FIELD" "$WORK/bundle/provider_alias_field_semantics_lite_v1.json"
cp "$SEM" "$WORK/bundle/provider_label_value_semantics_lite_v1.json"
cp "$RECON" "$WORK/bundle/cross_format_reconciliation_lite_v1.json"
cp "$METRIC" "$WORK/bundle/provider_metric_dictionary_lite_v1.json"
cp "$AGG" "$WORK/bundle/aggregate_definition_alignment_lite_v1.json"
cp "$ROW" "$WORK/bundle/row_nucleus_inventory_lite_v1.json"
cp "$EVIDENCE" "$WORK/bundle/evidence_atom_inventory_lite_v1.json"
cp "$IDENTITY" "$WORK/bundle/match_local_identity_candidates_lite_v1.json"
cp "$BUNDLES" "$WORK/bundle/semantic_role_action_bundle_candidates_lite_v1.json"
for log in "$WORK"/logs/*.txt; do
  cp "$log" "$WORK/bundle/$(basename "$log")"
done

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

cat "$VERIFY_TXT"
echo "PRODUCT_CODE_OK=$CODE_REAL"
echo "ACTIVE_MATCH_OK=$RUNTIME_REAL"
echo "BRANCH_OK=$ACTUAL_BRANCH"
echo "HEAD_OK=$ACTUAL_HEAD"
echo "OUTPUT=$ZIP"
