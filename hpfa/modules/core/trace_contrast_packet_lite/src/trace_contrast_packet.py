from __future__ import annotations

import hashlib, json, math
from collections import Counter
from typing import Any

MODULE_ID="trace_contrast_packet_lite_v1"
VARIANT_MODULE_ID="partial_order_trace_variant_lite_v1"
SIMILARITY_MODULE_ID="trace_similarity_primitive_lite_v1"
CANONICAL_EVENT_COUNT=TRUE_ACTION_COUNT="UNKNOWN"
CLAIM_CEILING="VISIBLE_TRACE_CONTRAST_CANDIDATE_ONLY"
ELIGIBILITY_COMPONENTS=("action","order","context")
SUCCESS_OUTCOMES={"TERMINAL_OUTCOME_SUPPORT_CANDIDATE"}
FAILURE_OUTCOMES={"OPPONENT_HANDOVER_CANDIDATE","OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE"}
NO_VISIBLE_OUTCOMES={"NO_VISIBLE_FOLLOW_UP_CANDIDATE"}

def _clean(v:Any)->str:return " ".join(str(v or "").split()).strip()
def _digest(*v:Any)->str:return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _status(p:dict[str,Any])->str:return _clean(p.get("status") or p.get("module_status")).upper() or "UNKNOWN"
def _pair_key(a:str,b:str)->tuple[str,str]:return tuple(sorted((a,b)))

def _validate_input(name:str,p:dict[str,Any],module_id:str):
    b=[]; r=[]
    if p.get("module_id")!=module_id:b.append(f"{name}_module_id_mismatch")
    if p.get("canonical_event_count")!=CANONICAL_EVENT_COUNT:b.append(f"{name}_canonical_event_count_claimed")
    if p.get("true_action_count") not in {None,TRUE_ACTION_COUNT}:b.append(f"{name}_true_action_count_claimed")
    if p.get("production_release") is True:b.append(f"{name}_production_release_claimed")
    if p.get("hard_block_hits"):b.append(f"{name}_hard_blocks_present")
    s=_status(p)
    if s=="FAIL_CLOSED":b.append(f"{name}_input_fail_closed")
    elif s=="REVIEW_REQUIRED":r.append(f"{name}_upstream_review_required")
    elif s!="PASS":r.append(f"{name}_upstream_status_review:{s}")
    return b,r

def _validate_eligibility(threshold:Any,weights:dict[str,Any]|None):
    b=[]
    try:t=float(threshold)
    except (TypeError,ValueError):return None,{},["eligibility_threshold_invalid"]
    if not math.isfinite(t) or not 0<=t<=1:b.append("eligibility_threshold_out_of_range")
    if not isinstance(weights,dict) or not weights:return t,{},b+["eligibility_weights_required"]
    c={}
    for k,v in weights.items():
        if k not in ELIGIBILITY_COMPONENTS:b.append(f"eligibility_component_forbidden:{k}");continue
        try:n=float(v)
        except (TypeError,ValueError):b.append(f"eligibility_weight_invalid:{k}");continue
        if not math.isfinite(n):b.append(f"eligibility_weight_non_finite:{k}");continue
        if n<0:b.append(f"eligibility_weight_negative:{k}");continue
        c[k]=n
    if not any(v>0 for v in c.values()):b.append("eligibility_positive_weight_required")
    return t,c,sorted(set(b))

def _eligibility_score(pair:dict[str,Any],weights:dict[str,float]):
    vals={"action":pair.get("action_similarity"),"order":pair.get("order_similarity"),"context":pair.get("context_similarity")}
    w=[]
    for k,wt in weights.items():
        if wt<=0:continue
        v=vals.get(k)
        if v is None:return None,f"INELIGIBLE_MISSING_REQUIRED_COMPONENT:{k}"
        try:n=float(v)
        except (TypeError,ValueError):return None,f"INELIGIBLE_INVALID_COMPONENT:{k}"
        if not math.isfinite(n) or not 0<=n<=1:return None,f"INELIGIBLE_OUT_OF_RANGE_COMPONENT:{k}"
        w.append((n,wt))
    d=sum(x for _,x in w)
    return (None,"INELIGIBLE_NO_WEIGHTED_COMPONENT") if d<=0 else (round(sum(v*x for v,x in w)/d,6),"AVAILABLE")

def _outcome_labels(v:dict[str,Any])->set[str]:
    out=set()
    for row in v.get("outcome_signature") or []:
        if not isinstance(row,dict):continue
        label=_clean(row.get("outcome_candidate"))
        try:count=int(row.get("count",0))
        except (TypeError,ValueError):count=0
        if label and count>0:out.add(label)
    return out

def _classify(v:dict[str,Any]):
    labels=_outcome_labels(v)
    s=bool(labels & SUCCESS_OUTCOMES); f=bool(labels & FAILURE_OUTCOMES); n=bool(labels & NO_VISIBLE_OUTCOMES); other=bool(labels-NO_VISIBLE_OUTCOMES)
    if n and not other:return "NO_VISIBLE_FOLLOWUP","NO_VISIBLE_FOLLOWUP",sorted(labels)
    if s and not f:return "SUCCESS","TERMINAL_SUCCESS_CANDIDATE",sorted(labels)
    if f and not s:return "FAILURE","LOSS_TERMINATION",sorted(labels)
    return "DIVERGENCE","VISIBLE_DIVERGENCE",sorted(labels)

def _fail(blocks,reviews):
    return {"module_id":MODULE_ID,"status":"FAIL_CLOSED","decision":"TRACE_CONTRAST_INPUT_REJECTED","trace_contrast_packets":[],"trace_contrast_packet_count":0,"hard_block_hits":sorted(set(blocks)),"review_hits":sorted(set(reviews)),"canonical_event_count":CANONICAL_EVENT_COUNT,"true_action_count":TRUE_ACTION_COUNT,"production_release":False,"claim_ceiling":CLAIM_CEILING}

def build_trace_contrast_packets(variant_payload:dict[str,Any],similarity_payload:dict[str,Any],*,minimum_similarity:Any,eligibility_weights:dict[str,Any]|None)->dict[str,Any]:
    blocks=[]; reviews=[]
    for name,p,mid in (("variant",variant_payload,VARIANT_MODULE_ID),("similarity",similarity_payload,SIMILARITY_MODULE_ID)):
        b,r=_validate_input(name,p,mid);blocks+=b;reviews+=r
    if variant_payload.get("same_timestamp_internal_ordering_allowed") is not False:blocks.append("variant_same_timestamp_policy_breached")
    if variant_payload.get("source_row_order_is_temporal_truth") is not False:blocks.append("variant_source_row_order_policy_breached")
    threshold,weights,b=_validate_eligibility(minimum_similarity,eligibility_weights);blocks+=b
    variants=[x for x in (variant_payload.get("partial_order_trace_variants") or []) if isinstance(x,dict)]
    byid={_clean(x.get("trace_variant_id")):x for x in variants if _clean(x.get("trace_variant_id"))}
    if len(byid)!=len(variants):blocks.append("variant_id_missing_or_duplicate")
    if len(variants)<2:blocks.append("missing_comparator_variant_population")
    for vid,v in byid.items():
        if not _outcome_labels(v):blocks.append(f"missing_visible_outcome_evidence:{vid}")
    pairs=[x for x in (similarity_payload.get("trace_similarity_pairs") or []) if isinstance(x,dict)]
    pairmap={}
    for p in pairs:
        a=_clean(p.get("trace_a_ref"));bref=_clean(p.get("trace_b_ref"))
        if not a or not bref or a==bref:blocks.append("similarity_pair_identity_invalid");continue
        k=_pair_key(a,bref)
        if k in pairmap:blocks.append(f"duplicate_similarity_pair:{k[0]}:{k[1]}")
        pairmap[k]=p
    ids=sorted(byid); expected={_pair_key(ids[i],ids[j]) for i in range(len(ids)) for j in range(i+1,len(ids))}
    if expected-set(pairmap):blocks.append("missing_similarity_comparator_pairs")
    if set(pairmap)-expected:blocks.append("similarity_pairs_reference_unknown_variant")
    if blocks:return _fail(blocks,reviews)
    outcomes={i:_classify(v) for i,v in byid.items()}; packets=[]; tv=float(threshold)
    for anchor in ids:
        eligible=[anchor]; evid=[]
        for other in ids:
            if other==anchor:continue
            score,state=_eligibility_score(pairmap[_pair_key(anchor,other)],weights); ok=score is not None and score>=tv
            evid.append({"trace_ref":other,"eligibility_similarity":score,"eligibility_state":state,"eligible":ok})
            if ok:eligible.append(other)
        succ=[];fail=[];div=[];nov=[];dist=Counter();states=Counter()
        for ref in eligible:
            bucket,state,_=outcomes[ref];dist[bucket]+=1;states[state]+=1
            {"SUCCESS":succ,"FAILURE":fail,"DIVERGENCE":div,"NO_VISIBLE_FOLLOWUP":nov}[bucket].append(ref)
        deps=sorted({_clean(x) for ref in eligible for x in (byid[ref].get("dependency_group_refs") or []) if _clean(x)})
        prov=sorted({_clean(x) for ref in eligible for x in (byid[ref].get("provenance_refs") or []) if _clean(x)})
        packet_state="CONTRAST_AVAILABLE"
        if len(eligible)<2:packet_state="REVIEW_REQUIRED_NO_ELIGIBLE_COMPARATOR";reviews.append(f"no_eligible_comparator:{anchor}")
        packets.append({"trace_contrast_id":"tcp_"+_digest(anchor,eligible,tv,weights)[:24],"anchor_trace_family":anchor,"anchor_context":byid[anchor].get("context_signature") or {},"eligible_trace_refs":eligible,"successful_trace_refs":succ,"failed_trace_refs":fail,"divergent_trace_refs":div,"no_visible_followup_refs":nov,"eligible_trace_count":len(eligible),"support_count":len(succ),"failure_count":len(fail),"divergence_count":len(div),"no_visible_followup_count":len(nov),"dependency_groups":deps,"independence_groups":[],"independent_support_count":"UNKNOWN","outcome_distribution":dict(sorted(dist.items())),"variant_distribution":dict(sorted(states.items())),"similarity_method":similarity_payload.get("method_version"),"similarity_parameters":{"minimum_similarity":tv,"eligibility_weights":dict(sorted(weights.items())),"allowed_components":list(ELIGIBILITY_COMPONENTS),"outcome_similarity_used_for_eligibility":False},"eligibility_rule":"SAME_RULE_FOR_ALL_OUTCOMES_WEIGHTED_ACTION_ORDER_CONTEXT_ONLY","pair_eligibility_evidence":evid,"counterevidence_refs":sorted(set(fail+div)),"alternative_explanation_refs":[],"provenance_refs":prov,"uncertainty":{"independence_not_proven":True,"no_visible_followup_is_failure":False,"absence_of_evidence_is_counterevidence":False,"similarity_threshold_is_objective_truth":False},"claim_ceiling":CLAIM_CEILING,"withdrawal_condition":"Withdraw or reclassify if occurrence binding, consequence classification, dependency accounting, or eligibility parameters change materially.","packet_state":packet_state,"trace_contrast_does_not_claim_causality":True,"trace_contrast_does_not_claim_intention":True,"canonical_event_count":CANONICAL_EVENT_COUNT,"true_action_count":TRUE_ACTION_COUNT})
    return {"module_id":MODULE_ID,"status":"REVIEW_REQUIRED" if reviews else "PASS","decision":"TRACE_CONTRAST_PACKETS_BUILT","trace_contrast_packets":packets,"trace_contrast_packet_count":len(packets),"source_trace_variant_count":len(variants),"source_similarity_pair_count":len(pairs),"hard_block_hits":[],"review_hits":sorted(set(reviews)),"similarity_method":similarity_payload.get("method_version"),"eligibility_threshold":tv,"eligibility_weights":dict(sorted(weights.items())),"no_visible_followup_is_failure":False,"absence_of_evidence_is_counterevidence":False,"success_failure_share_eligibility_contract":True,"dependent_reflections_are_independent_support":False,"trace_contrast_does_not_claim_causality":True,"canonical_event_count":CANONICAL_EVENT_COUNT,"true_action_count":TRUE_ACTION_COUNT,"production_release":False,"claim_ceiling":CLAIM_CEILING}
