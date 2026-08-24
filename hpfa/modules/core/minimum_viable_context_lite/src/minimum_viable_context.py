from __future__ import annotations

import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "minimum_viable_context_lite_v1"
CLAIM_SAFETY = "CONTEXT_CANDIDATE_ONLY"
OUTPUT_JSON = "minimum_viable_context_lite_v1.json"
OUTPUT_TXT = "minimum_viable_context_lite_v1.txt"
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".xml"}
ACTION_KEYS = ["action_family", "event_family", "event_type", "type", "action", "subtype", "code", "label", "text", "name"]
TEAM_KEYS = ["team", "team_name", "team_raw", "team_entity_key", "squad", "side"]
PERIOD_KEYS = ["period", "half", "match_period"]
X_KEYS = ["x", "x_meters", "start_x", "pos_x"]
Y_KEYS = ["y", "y_meters", "start_y", "pos_y"]
EXPLICIT_MINUTE_KEYS = {"minute", "minutes", "minute_raw", "match_minute"}
EXPLICIT_SECOND_KEYS = {"second", "seconds", "second_raw", "absolute_time_seconds", "match_second"}
AMBIGUOUS_TIME_KEYS = {"time", "timestamp", "timestamp_raw", "start", "end", "start_time", "end_time", "time_start", "time_end", "match_time", "game_time", "match_clock", "period_time", "tc", "t"}
XML_ACTION_TAGS = {"code", "label", "text", "action", "event", "event_type", "type", "subtype"}
XML_EVENT_TAGS = {"instance", "event", "row", "action"}
ORDERING_AUTHORITY = "PARTIAL_ORDER_ONLY"
MAX_FOOTBALL_MINUTE_CANDIDATE = 180

def repo_root_from_file() -> Path: return Path(__file__).resolve().parents[5]
def ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path: sys.path.insert(0, str(path))
def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"; ensure_module_path(src); import spine_runner; return spine_runner
def _lower_map(row): return {str(k).strip().lower(): v for k,v in row.items()}
def text_value(row, keys):
    lower=_lower_map(row)
    for key in keys:
        value=lower.get(key)
        if value not in (None,""): return str(value).strip()
    return "unknown"
def numeric_value(row, keys):
    lower=_lower_map(row)
    for key in keys:
        value=lower.get(key)
        if value in (None,""): continue
        try: return float(str(value).replace(",","."))
        except ValueError: continue
    return None
def normalize_action(text):
    value=text.lower()
    if "pass" in value:return "PASS"
    if any(t in value for t in ["shot","goal","save"]):return "SHOT"
    if any(t in value for t in ["carry","dribble"]):return "CARRY_DRIBBLE"
    if any(t in value for t in ["loss","turnover","dispossessed"]):return "BALL_LOSS"
    if any(t in value for t in ["recovery","interception"]):return "RECOVERY"
    if any(t in value for t in ["duel","challenge","pressure"]):return "DUEL_PRESSURE"
    if any(t in value for t in ["corner","throw","free kick","goal kick","restart","kick off"]):return "RESTART"
    if "foul" in value or "offside" in value:return "DEAD_BALL"
    return "UNKNOWN_OR_OTHER"
def _parse_number(value):
    if value in (None,""):return None
    try:return float(str(value).replace(",","."))
    except ValueError:return None
def _parse_clock_minute(value):
    text=str(value or "").strip()
    if not re.fullmatch(r"\d{1,3}:\d{2}(?::\d{2}(?:\.\d+)?)?",text):return None
    try: nums=[float(p) for p in text.split(":")]
    except ValueError:return None
    if len(nums)==2:
        m,s=nums
        if s>=60:return None
        minute=int(m+s/60)
    else:
        h,m,s=nums
        if m>=60 or s>=60:return None
        minute=int(h*60+m+s/60)
    return minute if 0<=minute<=MAX_FOOTBALL_MINUTE_CANDIDATE else None
def minute_bucket(value,unit=None):
    if unit=="MINUTE":
        n=_parse_number(value)
        if n is not None and 0<=n<=MAX_FOOTBALL_MINUTE_CANDIDATE:return str(int(n))
    elif unit=="SECOND":
        n=_parse_number(value)
        if n is not None and 0<=n<=MAX_FOOTBALL_MINUTE_CANDIDATE*60:return str(int(n//60))
    elif unit=="CLOCK":
        n=_parse_clock_minute(value)
        if n is not None:return str(n)
    return "unknown"
def resolve_time_evidence(row):
    admitted=[]; rejected=[]; raw=[]
    for raw_key,raw_value in row.items():
        key=str(raw_key).strip().lower()
        if raw_value in (None,""):continue
        if key in EXPLICIT_MINUTE_KEYS:
            raw.append({"field":str(raw_key),"raw_value":raw_value,"unit_candidate":"MINUTE"}); n=_parse_number(raw_value)
            if n is None:rejected.append({"field":str(raw_key),"raw_value":raw_value,"reason":"UNPARSEABLE_EXPLICIT_MINUTE"})
            elif not 0<=n<=MAX_FOOTBALL_MINUTE_CANDIDATE:rejected.append({"field":str(raw_key),"raw_value":raw_value,"reason":"IMPLAUSIBLE_EXPLICIT_MINUTE_RANGE"})
            else:admitted.append({"field":str(raw_key),"raw_value":raw_value,"unit":"MINUTE","minute_bucket":int(n),"basis":"EXPLICIT_MINUTE_FIELD"})
        elif key in EXPLICIT_SECOND_KEYS:
            raw.append({"field":str(raw_key),"raw_value":raw_value,"unit_candidate":"SECOND"}); n=_parse_number(raw_value)
            if n is None:rejected.append({"field":str(raw_key),"raw_value":raw_value,"reason":"UNPARSEABLE_EXPLICIT_SECOND"})
            elif not 0<=n<=MAX_FOOTBALL_MINUTE_CANDIDATE*60:rejected.append({"field":str(raw_key),"raw_value":raw_value,"reason":"IMPLAUSIBLE_EXPLICIT_SECOND_RANGE"})
            else:admitted.append({"field":str(raw_key),"raw_value":raw_value,"unit":"SECOND","minute_bucket":int(n//60),"basis":"EXPLICIT_SECOND_FIELD"})
        elif key in AMBIGUOUS_TIME_KEYS:
            raw.append({"field":str(raw_key),"raw_value":raw_value,"unit_candidate":"UNKNOWN"}); clock=_parse_clock_minute(raw_value)
            if clock is not None:admitted.append({"field":str(raw_key),"raw_value":raw_value,"unit":"CLOCK","minute_bucket":clock,"basis":"EXPLICIT_CLOCK_SHAPE"})
            else:rejected.append({"field":str(raw_key),"raw_value":raw_value,"reason":"UNKNOWN_TIME_UNIT"})
    minutes=sorted({int(x["minute_bucket"]) for x in admitted}); units=sorted({str(x["unit"]) for x in admitted})
    if len(minutes)>1:status="REVIEW_REQUIRED_TIME_CONFLICT"; minute=None; unit_status="CONFLICTED"; basis="CONFLICTING_ADMITTED_TIME_FIELDS"
    elif admitted:status="ADMITTED"; minute=minutes[0]; unit_status=units[0] if len(units)==1 else "MIXED_ADMITTED"; basis="+".join(sorted({str(x["basis"]) for x in admitted}))
    elif raw:status="REVIEW_REQUIRED_UNKNOWN_TIME_UNIT"; minute=None; unit_status="UNKNOWN"; basis="NO_SAFE_TIME_UNIT_ADMISSION"
    else:status="MISSING"; minute=None; unit_status="MISSING"; basis="NO_VISIBLE_TIME_FIELD"
    source=admitted[0] if len(admitted)==1 else None
    return {"time_admission_status":status,"time_field_admission_status":status,"time_unit_status":unit_status,"time_source_field":source.get("field") if source else None,"time_source_value":source.get("raw_value") if source else None,"time_derivation_basis":basis,"football_minute_candidate":minute,"minute_bucket":str(minute) if minute is not None else "unknown","raw_time_candidates":raw,"admitted_time_evidence":admitted,"rejected_time_field_candidates":rejected,"ordering_authority":ORDERING_AUTHORITY,"source_row_order_is_temporal_truth":False,"same_timestamp_internal_ordering_allowed":False}
def zone_candidate(x):
    if x is None:return "UNKNOWN_ZONE"
    if x<35:return "DEFENSIVE_THIRD"
    if x<70:return "MIDDLE_THIRD"
    return "FINAL_THIRD"
def channel_candidate(y):
    if y is None:return "UNKNOWN_CHANNEL"
    if y<22.67:return "LEFT_CHANNEL"
    if y<45.34:return "CENTRAL_CHANNEL"
    return "RIGHT_CHANNEL"
def context_completeness(row):
    score=sum([row.get("time_admission_status")=="ADMITTED",row["team_label"]!="unknown",row["action_family"]!="UNKNOWN_OR_OTHER",row["zone_candidate"]!="UNKNOWN_ZONE" and row["channel_candidate"]!="UNKNOWN_CHANNEL"])
    return "high" if score==4 else "medium" if score>=2 else "low"
def detect_delimiter(path):
    sample=path.read_text(encoding="utf-8",errors="ignore")[:4096]; first=(sample.splitlines() or [""])[0]
    if first.count(";")>first.count(",") and first.count(";")>=first.count("\t"):return ";"
    if first.count("\t")>first.count(","):return "\t"
    return ","
def read_csv_or_tsv(path,delimiter=None):
    delim=delimiter if delimiter is not None else detect_delimiter(path); rows=[]
    with path.open("r",encoding="utf-8",errors="ignore",newline="") as handle:
        for idx,row in enumerate(csv.DictReader(handle,delimiter=delim)):
            payload=dict(row); payload["_source_file"]=path.name; payload["_source_format"]=path.suffix.lower().lstrip("."); payload["_source_row_index"]=idx; rows.append(payload)
    return rows
def child_text(elem,tags):
    for child in elem.iter():
        if child is elem:continue
        text=(child.text or "").strip()
        if child.tag.lower() in tags and text:return text
        for key,value in child.attrib.items():
            if key.lower() in tags and value:return str(value).strip()
    return None
def is_xml_event_node(elem):
    tag=elem.tag.lower()
    if tag in XML_EVENT_TAGS and (dict(elem.attrib) or list(elem)):return True
    return child_text(elem,XML_ACTION_TAGS) is not None and tag not in {"file","all_instances","sort_info","label"}
def flatten_xml_event(elem,path,idx):
    payload=dict(elem.attrib); action_text=child_text(elem,XML_ACTION_TAGS)
    if action_text:payload.setdefault("event_type",action_text); payload.setdefault("code",action_text)
    for child in elem.iter():
        if child is elem:continue
        text=(child.text or "").strip()
        if text:payload.setdefault(child.tag,text)
        for key,value in child.attrib.items():
            if value:payload.setdefault(key,value)
    payload["_source_file"]=path.name; payload["_source_format"]="xml"; payload["_source_row_index"]=idx; return payload
def read_xml(path):
    try:root=ET.parse(path).getroot()
    except ET.ParseError:return []
    events=[e for e in root.iter() if e is not root and is_xml_event_node(e)]; return [flatten_xml_event(e,path,i) for i,e in enumerate(events)]
def discover_rows(input_dir):
    root=Path(input_dir).expanduser().resolve(strict=False); rows=[]
    for path in sorted(root.iterdir() if root.exists() else []):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:continue
        if path.suffix.lower()==".csv":rows.extend(read_csv_or_tsv(path))
        elif path.suffix.lower()==".tsv":rows.extend(read_csv_or_tsv(path,"\t"))
        elif path.suffix.lower()==".xml":rows.extend(read_xml(path))
    return rows
def build_context_candidates(rows):
    candidates=[]
    for idx,row in enumerate(rows):
        x=numeric_value(row,X_KEYS); y=numeric_value(row,Y_KEYS); c={"context_id":f"ctx_{idx:06d}","source_file":str(row.get("_source_file","unknown")),"source_format":str(row.get("_source_format","unknown")),"source_row_index":row.get("_source_row_index",idx),"period":text_value(row,PERIOD_KEYS),"team_label":text_value(row,TEAM_KEYS).lower(),"action_family":normalize_action(text_value(row,ACTION_KEYS)),"zone_candidate":zone_candidate(x),"channel_candidate":channel_candidate(y),"previous_action_family":"UNKNOWN_PREVIOUS_ACTION","next_action_family":"UNKNOWN_NEXT_ACTION","synthetic_previous_next_adjacency_allowed":False,"source_confidence":"surface_candidate_only","claim_allowed":False}; c.update(resolve_time_evidence(row));
        if isinstance(row.get("_preserved_unmapped"),dict):c["_preserved_unmapped"]=dict(row["_preserved_unmapped"])
        c["context_completeness"]=context_completeness(c); candidates.append(c)
    return candidates
def summarize(candidates):
    return {"context_completeness_counts":dict(sorted(Counter(str(x.get("context_completeness","unknown")) for x in candidates).items())),"action_family_counts":dict(sorted(Counter(str(x.get("action_family","UNKNOWN_OR_OTHER")) for x in candidates).items())),"time_admission_status_counts":dict(sorted(Counter(str(x.get("time_admission_status","MISSING")) for x in candidates).items())),"time_unit_status_counts":dict(sorted(Counter(str(x.get("time_unit_status","MISSING")) for x in candidates).items())),"time_source_field_counts":dict(sorted(Counter(str(x.get("time_source_field")) for x in candidates if x.get("time_source_field")).items()))}
def build_report(input_dir,root=None):
    repo_root=Path(root).resolve() if root is not None else repo_root_from_file(); rows=discover_rows(input_dir); candidates=build_context_candidates(rows); summary=summarize(candidates)
    return {"module_id":MODULE_ID,"status":"REVIEW_REQUIRED","decision":"CONTEXT_CANDIDATES_ONLY","claim_safety":CLAIM_SAFETY,"surface_row_count":len(rows),"context_candidate_count":len(candidates),"context_candidates":candidates,"context_candidates_sample":candidates[:200],"context_summary":summary,"time_admission_status":"ADMITTED" if candidates and all(x.get("time_admission_status")=="ADMITTED" for x in candidates) else "REVIEW_REQUIRED","ordering_authority":ORDERING_AUTHORITY,"source_row_order_is_temporal_truth":False,"same_timestamp_internal_ordering_allowed":False,"canonical_event_count":"UNKNOWN","deduplicated_event_count":"UNKNOWN","true_action_count":"UNKNOWN","phase_truth":False,"possession_truth":False,"sequence_truth":False,"tactical_truth":False,"dominance_truth":False,"analyst_sentence_allowed":False,"claim_allowed":False,"production_release":False,"repo_root":str(repo_root)}
def render_txt(report):
    return "\n".join(["HPFA MINIMUM VIABLE CONTEXT LITE V1","====================================",f"status={report.get('status')}",f"surface_row_count={report.get('surface_row_count')}",f"context_candidate_count={report.get('context_candidate_count')}",f"time_admission_status={report.get('time_admission_status')}",f"context_summary={json.dumps(report.get('context_summary',{}),ensure_ascii=False,sort_keys=True)}","source_row_order_is_temporal_truth=false","same_timestamp_internal_ordering_allowed=false","canonical_event_count=UNKNOWN","true_action_count=UNKNOWN","production_release=false",""])
def write_outputs(input_dir,out_dir,root=None):
    repo_root=Path(root).resolve() if root is not None else repo_root_from_file(); spine=spine_runner_module(repo_root); output_root=spine.validate_output_root(out_dir); output_root.mkdir(parents=True,exist_ok=True); report=build_report(input_dir,root=repo_root); json_out=output_root/OUTPUT_JSON; txt_out=output_root/OUTPUT_TXT; report["outputs"]={"json":str(json_out),"txt":str(txt_out)}; json_out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8"); txt_out.write_text(render_txt(report),encoding="utf-8"); return report
