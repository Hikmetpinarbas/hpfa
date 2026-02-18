#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HPFA_REPO="${HOME}/hpfa"
F="${HPFA_REPO}/_diag/doctor_history.tsv"

if [ ! -f "${F}" ]; then
  echo "[FAIL] doctor_history.tsv not found: ${F}" >&2
  exit 2
fi

TS="$(date +%Y%m%d_%H%M%S)"
BK="${F}.BAK_${TS}"

cp -f "${F}" "${BK}"

# Normalize to 7 columns:
# 1 ts
# 2 tag
# 3 repo_head
# 4 stable_head
# 5 doctor (PASS/FAIL/0/--help etc.)
# 6 fail (int)
# 7 primary_dir (path or empty)
awk -F'\t' -v OFS='\t' '
function is_ts(x){ return x ~ /^[0-9]{4}-[0-9]{2}-[0-9]{2}T/ }
function trim(s){ sub(/^[ \t]+/,"",s); sub(/[ \t]+$/,"",s); return s }

BEGIN{
  # pending path line attaches to previous record
  have_prev=0
  prev_ts=""; prev_tag=""; prev_rh=""; prev_sh=""; prev_doc=""; prev_fail=""; prev_dir=""
}

# Flush previous record if exists
function flush_prev(){
  if(have_prev==1){
    print prev_ts, prev_tag, prev_rh, prev_sh, prev_doc, prev_fail, prev_dir
    have_prev=0
    prev_ts=""; prev_tag=""; prev_rh=""; prev_sh=""; prev_doc=""; prev_fail=""; prev_dir=""
  }
}

{
  # If line starts with a timestamp => new record (or record fragment)
  if(is_ts($1)){
    # New record begins; flush previous pending record first
    flush_prev()

    # Defensive parse:
    # Some older lines may have 6 fields without primary_dir.
    # Some may have 7 fields.
    ts=trim($1)
    tag=trim($2)
    rh=trim($3)
    sh=trim($4)
    doc=trim($5)
    fail=trim($6)
    dir=(NF>=7? trim($7) : "")

    # If fail is missing/empty, force 0
    if(fail==""){ fail="0" }

    # Hold as previous (may get a path continuation line next)
    have_prev=1
    prev_ts=ts; prev_tag=tag; prev_rh=rh; prev_sh=sh; prev_doc=doc; prev_fail=fail; prev_dir=dir
    next
  }

  # Non-timestamp line: treat as primary_dir continuation if it looks like a path
  # Your file shows path lines in column1 and "0" in column6-ish; we just take the path.
  path=trim($1)
  if(have_prev==1 && path ~ /^\//){
    # attach only if prev_dir empty
    if(prev_dir==""){
      prev_dir=path
    } else {
      # if already has dir, keep both as semi-colon
      prev_dir=prev_dir ";" path
    }
    next
  }

  # Otherwise ignore line but keep fail-closed trace by appending as comment into dir
  if(have_prev==1){
    prev_dir=prev_dir ";UNPARSED_LINE:" trim($0)
  }
}

END{
  flush_prev()
}
' "${BK}" > "${F}"

echo "[OK] normalized: ${F}"
echo "[OK] backup: ${BK}"
echo "[CHECK] sample:"
tail -n 12 "${F}" || true
