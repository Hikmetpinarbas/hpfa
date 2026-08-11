from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

MODULE_ID = "aggregate_derivation_evidence_reconciliation_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "AGGREGATE_DERIVATION_EVIDENCE_RECONCILIATION_CANDIDATE_ONLY"
EXPECTED_MODULES = {
    "xlsx": "xlsx_entity_metric_row_projection_lite_v1",
    "atoms": "evidence_atom_inventory_lite_v1",
    "identity": "match_local_identity_candidates_lite_v1",
    "semantics": "provider_label_value_semantics_lite_v1",
    "alignment": "aggregate_definition_alignment_lite_v1",
}
OUTPUTS = {
    "json": "aggregate_derivation_evidence_reconciliation_lite_v1.json",
    "summary": "aggregate_derivation_evidence_reconciliation_lite_v1.txt",
    "analyst": "aggregate_derivation_evidence_reconciliation_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_identity_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text)).strip("_")


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    raw = str(path)
    if raw.startswith("/sdcard/Download/HPFA/") or raw.startswith("/storage/emulated/0/Download/HPFA/"):
        raise ValueError("nested_phone_output_directory_rejected")
    return Path(path).expanduser().resolve(strict=False)


def _active_match_path(path: Path) -> bool:
    parts = path.resolve(strict=False).parts
    return len(parts) >= 3 and tuple(parts[-3:]) == ("runtime", "active_single_match", "current")


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("upstream_output_unreadable_or_malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("upstream_output_not_object")
    return payload


def _guard_payload(payload: dict[str, Any], expected_module: str, role: str) -> tuple[list[str], list[str]]:
    blocks: list[str] = []
    reviews: list[str] = []
    if payload.get("module_id") != expected_module:
        blocks.append(f"upstream_module_id_mismatch:{role}")
    if payload.get("status") == "FAIL_CLOSED" or payload.get("module_status") == "FAIL_CLOSED":
        blocks.append(f"upstream_fail_closed:{role}")
    if payload.get("hard_block_hits"):
        blocks.append(f"upstream_hard_blocks_present:{role}")
    if payload.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"canonical_event_count_claimed:{role}")
    if payload.get("production_release") is True:
        blocks.append(f"unexpected_production_claim:{role}")
    status = str(payload.get("status") or payload.get("module_status") or "UNKNOWN")
    if status not in {"PASS", "SMOKE_PASS"} and status != "FAIL_CLOSED":
        reviews.append(f"upstream_review_preserved:{role}:{status}")
    return blocks, reviews


def _unique_index(rows: list[dict[str, Any]], key_name: str) -> tuple[dict[str, dict[str, Any]], list[str]]:
    index: dict[str, dict[str, Any]] = {}
    blocks: list[str] = []
    for i, row in enumerate(rows):
        key = _clean(row.get(key_name))
        if not key:
            blocks.append(f"{key_name}_missing:{i}")
            continue
        if key in index:
            blocks.append(f"duplicate_{key_name}:{key}")
            continue
        index[key] = row
    return index, blocks


def _supported_precision(number_format: Any) -> int | None:
    match = re.fullmatch(r"0(?:\.(0+))?%", _clean(number_format))
    if not match:
        return None
    return len(match.group(1) or "")


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _display_percent(value_ratio: Decimal, precision: int) -> Decimal:
    quantum = Decimal("1").scaleb(-precision)
    return (value_ratio * Decimal(100)).quantize(quantum, rounding=ROUND_HALF_UP)


def _definition_registry_index(registry: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    index: dict[str, dict[str, Any]] = {}
    blocks: list[str] = []
    if not isinstance(registry.get("definitions"), list) or not registry.get("definitions"):
        return {}, ["definition_registry_empty"]
    for i, row in enumerate(registry["definitions"]):
        if not isinstance(row, dict):
            blocks.append(f"definition_record_invalid:{i}")
            continue
        definition_id = _clean(row.get("definition_id"))
        if not definition_id:
            blocks.append(f"definition_id_missing:{i}")
            continue
        if definition_id in index:
            blocks.append(f"duplicate_definition_id:{definition_id}")
            continue
        index[definition_id] = row
    return index, blocks


def _semantic_requirements(definition: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    requirements = definition.get("required_occurrence_semantics") or []
    if not isinstance(requirements, list):
        return None, None, ["required_occurrence_semantics_invalid"]
    success = [row for row in requirements if isinstance(row, dict) and row.get("outcome_candidate") == "SUCCESS"]
    failure = [row for row in requirements if isinstance(row, dict) and row.get("outcome_candidate") == "FAILURE"]
    blocks: list[str] = []
    if len(success) != 1:
        blocks.append(f"success_semantic_contract_not_single:{len(success)}")
    if len(failure) != 1:
        blocks.append(f"failure_semantic_contract_not_single:{len(failure)}")
    return success[0] if len(success) == 1 else None, failure[0] if len(failure) == 1 else None, blocks


def _requirement_supported(alignment_row: dict[str, Any], requirement: dict[str, Any]) -> bool:
    for support in alignment_row.get("semantic_support", []) or []:
        if support.get("requirement") == requirement and int(support.get("match_count") or 0) > 0:
            return True
    return False


def _atom_matches_requirement(atom: dict[str, Any], requirement: dict[str, Any]) -> bool:
    if atom.get("atom_class") != "ACTION_ANCHOR_ATOM" or atom.get("atom_status") != "PASS":
        return False
    roles = {str(v) for v in (requirement.get("source_roles") or [])}
    if atom.get("source_role") not in roles:
        return False
    if atom.get("normalized_label") != requirement.get("normalized_label"):
        return False
    if requirement.get("action_family_candidate") not in (atom.get("action_family_candidates") or []):
        return False
    if requirement.get("outcome_candidate") not in (atom.get("outcome_candidates") or []):
        return False
    if "EXACT_REVIEWED_CANDIDATE" not in (atom.get("mapping_statuses") or []):
        return False
    return True


def _find_aggregate_cell(row: dict[str, Any], aggregate_label: str) -> tuple[dict[str, Any] | None, list[str]]:
    matches = [cell for cell in (row.get("metric_values") or {}).values() if isinstance(cell, dict) and cell.get("raw_metric_label") == aggregate_label]
    if len(matches) != 1:
        return None, [f"aggregate_metric_cell_not_single:{len(matches)}"]
    cell = matches[0]
    if cell.get("value_admitted") is not True:
        return None, ["aggregate_metric_cell_not_admitted"]
    return cell, []


def _alignment_index(payload: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    return _unique_index([row for row in payload.get("alignment_rows", []) if isinstance(row, dict)], "definition_id")


def _identity_indexes(payload: dict[str, Any]):
    team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actor: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("team_identity_candidates", []) or []:
        if row.get("decision_state") == "TEAM_IDENTITY_CANDIDATE_BOUND":
            team[str(row.get("team_normalized_key") or "")].append(row)
    for row in payload.get("actor_identity_candidates", []) or []:
        if row.get("decision_state") == "ACTOR_IDENTITY_CANDIDATE_BOUND":
            actor[(str(row.get("team_normalized_key") or ""), str(row.get("actor_normalized_key") or ""))].append(row)
    return team, actor


def build_reconciliation(
    xlsx_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    identity_payload: dict[str, Any],
    semantics_payload: dict[str, Any],
    alignment_payload: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    for role, payload in (("xlsx", xlsx_payload), ("atoms", evidence_payload), ("identity", identity_payload), ("semantics", semantics_payload), ("alignment", alignment_payload)):
        b, r = _guard_payload(payload, EXPECTED_MODULES[role], role)
        blocks.extend(b)
        reviews.extend(r)

    binding = _clean(identity_payload.get("match_surface_binding_id"))
    if not binding:
        blocks.append("match_surface_binding_missing")
    if binding and evidence_payload.get("match_surface_binding_id") != binding:
        blocks.append("match_surface_binding_mismatch:atoms_identity")

    atom_index, atom_blocks = _unique_index([row for row in evidence_payload.get("evidence_atoms", []) if isinstance(row, dict)], "evidence_atom_id")
    binding_index, binding_blocks = _unique_index([row for row in identity_payload.get("identity_bindings", []) if isinstance(row, dict)], "evidence_atom_id")
    definition_index, definition_blocks = _definition_registry_index(registry)
    alignment_index, alignment_blocks = _alignment_index(alignment_payload)
    blocks.extend(atom_blocks + binding_blocks + definition_blocks + alignment_blocks)
    if binding:
        for evidence_id, atom in atom_index.items():
            if atom.get("match_surface_binding_id") != binding:
                blocks.append(f"evidence_atom_match_surface_binding_mismatch:{evidence_id}")
        for evidence_id, identity_binding in binding_index.items():
            if identity_binding.get("match_surface_binding_id") != binding:
                blocks.append(f"identity_binding_match_surface_binding_mismatch:{evidence_id}")
    if semantics_payload.get("provider_label_records") is None:
        blocks.append("provider_label_records_missing")

    team_index, actor_index = _identity_indexes(identity_payload)
    records: list[dict[str, Any]] = []

    if not blocks:
        for definition_id, definition in sorted(definition_index.items()):
            alignment_row = alignment_index.get(definition_id)
            if alignment_row is None:
                blocks.append(f"aggregate_alignment_definition_missing:{definition_id}")
                continue
            success_req, failure_req, req_blocks = _semantic_requirements(definition)
            if req_blocks:
                blocks.extend(f"{definition_id}:{item}" for item in req_blocks)
                continue
            assert success_req is not None and failure_req is not None
            contract_observed = _requirement_supported(alignment_row, success_req) and _requirement_supported(alignment_row, failure_req)
            allowed_roles = {str(v) for v in (definition.get("source_roles") or [])}

            for file_row in xlsx_payload.get("files", []) or []:
                for sheet in file_row.get("sheets", []) or []:
                    for row in sheet.get("rows", []) or []:
                        if row.get("source_role") not in allowed_roles:
                            continue
                        row_reviews: list[str] = []
                        row_blocks: list[str] = []
                        raw_identity = row.get("identity_candidates") or {}
                        team_key = normalize_identity_key(raw_identity.get("team_raw_candidate"))
                        actor_key = normalize_identity_key(raw_identity.get("player_raw_candidate"))
                        teams = team_index.get(team_key, [])
                        actors = actor_index.get((team_key, actor_key), [])
                        if len(teams) != 1:
                            row_reviews.append(f"team_entity_candidate_not_single:{len(teams)}")
                        if len(actors) != 1:
                            row_reviews.append(f"actor_entity_candidate_not_single:{len(actors)}")
                        team_row = teams[0] if len(teams) == 1 else None
                        actor_row = actors[0] if len(actors) == 1 else None
                        if team_row and actor_row and actor_row.get("team_identity_candidate_id") != team_row.get("team_identity_candidate_id"):
                            row_blocks.append("actor_team_candidate_inconsistent")
                        team_id = team_row.get("team_identity_candidate_id") if team_row else None
                        actor_id = actor_row.get("actor_identity_candidate_id") if actor_row else None

                        cell, cell_hits = _find_aggregate_cell(row, str(definition.get("aggregate_label") or ""))
                        row_reviews.extend(cell_hits)
                        if not contract_observed:
                            row_reviews.append("required_semantic_contract_support_unresolved")

                        success_ids: set[str] = set()
                        failure_ids: set[str] = set()
                        semantic_near_miss_ids: set[str] = set()
                        if actor_id and team_id and contract_observed:
                            required_labels = {success_req.get("normalized_label"), failure_req.get("normalized_label")}
                            for evidence_id, atom in atom_index.items():
                                identity_binding = binding_index.get(evidence_id)
                                if not identity_binding or identity_binding.get("decision_state") != "ACTOR_IDENTITY_CANDIDATE_BOUND":
                                    continue
                                if identity_binding.get("match_surface_binding_id") != binding:
                                    continue
                                if identity_binding.get("actor_identity_candidate_id") != actor_id or identity_binding.get("team_identity_candidate_id") != team_id:
                                    continue
                                success_match = _atom_matches_requirement(atom, success_req)
                                failure_match = _atom_matches_requirement(atom, failure_req)
                                if success_match:
                                    success_ids.add(evidence_id)
                                if failure_match:
                                    failure_ids.add(evidence_id)
                                if atom.get("normalized_label") in required_labels and not (success_match or failure_match):
                                    semantic_near_miss_ids.add(evidence_id)

                        overlap = success_ids & failure_ids
                        if overlap:
                            row_blocks.append("semantic_component_collision")
                        if semantic_near_miss_ids:
                            row_reviews.append("contradictory_or_ineligible_semantic_support_present")
                        numerator = len(success_ids)
                        failure_count = len(failure_ids)
                        denominator = numerator + failure_count
                        zero_state = "ZERO_DENOMINATOR" if denominator == 0 else "NONZERO_DENOMINATOR"

                        exact_ratio: Decimal | None = None
                        arithmetic_percentage: Decimal | None = None
                        delta: Decimal | None = None
                        observed_display: Decimal | None = None
                        computed_display: Decimal | None = None
                        comparison_method = "NOT_COMPUTABLE"
                        arithmetic_status = "ARITHMETIC_CANDIDATE_NOT_COMPUTABLE"
                        raw_value = cell.get("raw_value") if cell else None
                        raw_decimal = _decimal(raw_value) if cell and cell.get("value_kind") == "number" else None
                        if denominator > 0 and raw_decimal is not None:
                            exact_ratio = Decimal(numerator) / Decimal(denominator)
                            arithmetic_percentage = exact_ratio * Decimal(100)
                            delta = raw_decimal - exact_ratio
                            if raw_decimal == exact_ratio:
                                arithmetic_status = "ARITHMETIC_CANDIDATE_REPRODUCED"
                                comparison_method = "EXACT_NUMERIC_RATIO_EQUALITY"
                            else:
                                precision = _supported_precision(cell.get("number_format"))
                                if precision is not None:
                                    observed_display = _display_percent(raw_decimal, precision)
                                    computed_display = _display_percent(exact_ratio, precision)
                                    comparison_method = "OBSERVED_SIMPLE_PERCENT_DISPLAY_PRECISION"
                                    arithmetic_status = "ARITHMETIC_CANDIDATE_REPRODUCED" if observed_display == computed_display else "ARITHMETIC_CANDIDATE_MISMATCH"
                                else:
                                    comparison_method = "UNSUPPORTED_DISPLAY_FORMAT_NO_TOLERANCE"
                                    arithmetic_status = "ARITHMETIC_CANDIDATE_MISMATCH"

                        scope_ok = bool(team_row and actor_row and not row_blocks)
                        scope_status = "SCOPE_ALIGNMENT_CANDIDATE" if scope_ok else "SCOPE_ALIGNMENT_REVIEW_REQUIRED"
                        lineage_complete = bool(scope_ok and cell is not None and contract_observed and not overlap and not semantic_near_miss_ids and binding)
                        lineage_status = "DERIVATION_LINEAGE_CANDIDATE_COMPLETE" if lineage_complete else "DERIVATION_LINEAGE_REVIEW_REQUIRED"
                        provider_status = "PROVIDER_DEFINITION_REVIEWED_CANDIDATE" if definition.get("definition_evidence_status") == "REVIEWED_PROVIDER_DEFINITION_CANDIDATE" else "PROVIDER_DEFINITION_REQUIRED"
                        if provider_status == "PROVIDER_DEFINITION_REQUIRED":
                            row_reviews.append("provider_definition_evidence_required")
                        g16_admitted = bool(lineage_complete and not row_blocks)
                        g16_status = "G16_RECHECK_ADMITTED" if g16_admitted else "G16_RECHECK_BLOCKED"
                        if not g16_admitted and not row_reviews and not row_blocks:
                            row_reviews.append("g16_recheck_not_admitted")

                        records.append({
                            "reconciliation_record_id": "adr_" + _digest(definition_id, binding, row.get("row_projection_id"), actor_id)[:24],
                            "definition_id": definition_id,
                            "provider_id": definition.get("provider_id"),
                            "provider_version": definition.get("provider_version"),
                            "match_surface_binding_id": binding or None,
                            "source_role": row.get("source_role"),
                            "entity_scope_candidate": actor_id,
                            "team_identity_candidate_id": team_id,
                            "actor_identity_candidate_id": actor_id,
                            "observation_scope_candidate": "MATCH_FILE_AGGREGATE_TO_VISIBLE_OCCURRENCE_SCOPE_CANDIDATE",
                            "xlsx_row_projection_id": row.get("row_projection_id"),
                            "xlsx_relative_path": row.get("relative_path"),
                            "xlsx_source_sha256": row.get("source_sha256"),
                            "xlsx_sheet_name": row.get("sheet_name"),
                            "xlsx_source_row_number": row.get("source_row_number"),
                            "aggregate_label": definition.get("aggregate_label"),
                            "aggregate_value_observed": raw_value,
                            "aggregate_value_kind": cell.get("value_kind") if cell else None,
                            "aggregate_number_format": cell.get("number_format") if cell else None,
                            "numerator_semantic_contract": success_req,
                            "denominator_semantic_contract": [success_req, failure_req],
                            "numerator_support_record_ids": sorted(success_ids),
                            "denominator_support_record_ids": sorted(success_ids | failure_ids),
                            "failure_component_support_record_ids": sorted(failure_ids),
                            "semantic_near_miss_record_ids": sorted(semantic_near_miss_ids),
                            "numerator_observed_candidate": numerator,
                            "denominator_observed_candidate": denominator,
                            "failure_component_observed_candidate": failure_count,
                            "zero_denominator_state": zero_state,
                            "exact_ratio_candidate": float(exact_ratio) if exact_ratio is not None else None,
                            "arithmetic_percentage_candidate": float(arithmetic_percentage) if arithmetic_percentage is not None else None,
                            "arithmetic_comparison_method": comparison_method,
                            "observed_display_value_candidate": float(observed_display) if observed_display is not None else None,
                            "computed_display_value_candidate": float(computed_display) if computed_display is not None else None,
                            "provider_rounding_delta_candidate": float(delta) if delta is not None else None,
                            "provider_rounding_delta_claim_ceiling": "OBSERVED_NUMERIC_DELTA_CANDIDATE_ONLY",
                            "observed_arithmetic_status": arithmetic_status,
                            "scope_alignment_status": scope_status,
                            "derivation_lineage_status": lineage_status,
                            "provider_definition_evidence_status": provider_status,
                            "independence_status": definition.get("independence_status"),
                            "g16_recheck_admission": g16_status,
                            "validated_player_identity": False,
                            "validated_team_identity": False,
                            "hard_block_hits": sorted(set(row_blocks)),
                            "review_hits": sorted(set(row_reviews)),
                        })

    if not records and not blocks:
        reviews.append("no_reconciliation_records_produced")
    if any(record["hard_block_hits"] for record in records):
        blocks.append("record_level_hard_blocks_present")
    if any(record["review_hits"] for record in records):
        reviews.append("record_level_review_required")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    admitted_count = sum(row["g16_recheck_admission"] == "G16_RECHECK_ADMITTED" for row in records)
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "match_surface_binding_id": binding or None,
        "reconciliation_records": records,
        "reconciliation_record_count": len(records),
        "g16_recheck_admitted_count": admitted_count,
        "g16_recheck_blocked_count": len(records) - admitted_count,
        "observed_arithmetic_status_counts": dict(sorted(Counter(row["observed_arithmetic_status"] for row in records).items())),
        "scope_alignment_status_counts": dict(sorted(Counter(row["scope_alignment_status"] for row in records).items())),
        "derivation_lineage_status_counts": dict(sorted(Counter(row["derivation_lineage_status"] for row in records).items())),
        "provider_definition_evidence_status_counts": dict(sorted(Counter(row["provider_definition_evidence_status"] for row in records).items())),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "g16_pass_claimed": False,
        "arithmetic_reproduction_is_provider_definition_truth": False,
        "arithmetic_reproduction_is_metric_truth": False,
        "same_provider_is_independent_confirmation": False,
        "aggregate_equivalence_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _runtime_status(status: str, active: bool) -> str:
    if not active:
        return "NOT_EVALUATED"
    return f"ACTIVE_MATCH_EXECUTION_COMPLETED_{status if status in {'PASS', 'REVIEW_REQUIRED', 'FAIL_CLOSED'} else 'REVIEW_REQUIRED'}"


def write_outputs(
    xlsx_path: str | Path,
    evidence_path: str | Path,
    identity_path: str | Path,
    semantics_path: str | Path,
    alignment_path: str | Path,
    registry_path: str | Path,
    out: str | Path,
    *,
    runtime_authority: str | Path | None = None,
    active_match_execution: bool = False,
) -> dict[str, Any]:
    out_dir = validate_out(out)
    if active_match_execution and (runtime_authority is None or not _active_match_path(Path(runtime_authority))):
        raise ValueError("active_match_runtime_authority_mismatch")
    payload = build_reconciliation(load_json(xlsx_path), load_json(evidence_path), load_json(identity_path), load_json(semantics_path), load_json(alignment_path), load_json(registry_path))
    payload["runtime_evidence_status"] = _runtime_status(str(payload.get("status")), active_match_execution)
    payload["runtime_authority"] = str(Path(runtime_authority).expanduser().resolve(strict=False)) if active_match_execution and runtime_authority else None
    payload["active_match_evidence_pass"] = bool(active_match_execution and payload.get("status") != "FAIL_CLOSED")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUTPUTS["json"]).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / OUTPUTS["summary"]).write_text("\n".join([
        "HPFA AGGREGATE DERIVATION EVIDENCE RECONCILIATION LITE V1",
        f"status={payload.get('status')}",
        f"runtime_evidence_status={payload.get('runtime_evidence_status')}",
        f"reconciliation_record_count={payload.get('reconciliation_record_count')}",
        f"g16_recheck_admitted_count={payload.get('g16_recheck_admitted_count')}",
        f"g16_recheck_blocked_count={payload.get('g16_recheck_blocked_count')}",
        f"observed_arithmetic_status_counts={payload.get('observed_arithmetic_status_counts')}",
        f"provider_definition_evidence_status_counts={payload.get('provider_definition_evidence_status_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ]), encoding="utf-8")
    lines = [
        "HPFA AGGREGATE DERIVATION EVIDENCE RECONCILIATION ANALYST AUDIT",
        "This surface asks whether exact row-level semantic evidence can reproduce an observed XLSX aggregate for the same match-local entity candidate.",
        "Arithmetic reproduction does not validate the provider definition, player identity, metric truth, or comparison truth.",
    ]
    for row in payload.get("reconciliation_records", []):
        lines.append("entity={entity} aggregate={aggregate} numerator={num} denominator={den} arithmetic={arith} recheck={recheck}".format(
            entity=row.get("actor_identity_candidate_id"), aggregate=row.get("aggregate_value_observed"), num=row.get("numerator_observed_candidate"), den=row.get("denominator_observed_candidate"), arith=row.get("observed_arithmetic_status"), recheck=row.get("g16_recheck_admission")
        ))
    lines.extend(["canonical_event_count=UNKNOWN", "production_release=false"])
    (out_dir / OUTPUTS["analyst"]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx-row-projection", required=True)
    parser.add_argument("--evidence-atoms", required=True)
    parser.add_argument("--identity-candidates", required=True)
    parser.add_argument("--label-semantics", required=True)
    parser.add_argument("--aggregate-alignment", required=True)
    parser.add_argument("--definition-registry", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runtime-authority")
    parser.add_argument("--active-match-execution", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = write_outputs(args.xlsx_row_projection, args.evidence_atoms, args.identity_candidates, args.label_semantics, args.aggregate_alignment, args.definition_registry, args.out, runtime_authority=args.runtime_authority, active_match_execution=args.active_match_execution)
    except ValueError as exc:
        print(json.dumps({"module_id": MODULE_ID, "status": "FAIL_CLOSED", "hard_block_hits": [str(exc)], "canonical_event_count": CANONICAL_EVENT_COUNT, "production_release": False}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"module_id": MODULE_ID, "status": payload.get("status"), "runtime_evidence_status": payload.get("runtime_evidence_status"), "reconciliation_record_count": payload.get("reconciliation_record_count"), "g16_recheck_admitted_count": payload.get("g16_recheck_admitted_count"), "canonical_event_count": CANONICAL_EVENT_COUNT, "production_release": False}, ensure_ascii=False, indent=2))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
