#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"

DOCTOR="$REPO/tools/hpfa-doctor"
PACKDOC="$REPO/tools/hpfa_pack_doctor.sh"
VAL="$REPO/tools/hpfa_validator_run_strict_core.sh"

fail(){ echo "[FAIL] $*" >&2; exit 1; }
ok(){ echo "[OK] $*"; }

[ -x "$DOCTOR" ] || fail "doctor missing: $DOCTOR"
[ -x "$PACKDOC" ] || fail "pack doctor missing: $PACKDOC"
[ -x "$VAL" ] || fail "validator missing: $VAL"

ok "gate start: $(date -Iseconds)"

"$DOCTOR"
ok "doctor PASS"

"$PACKDOC"
ok "pack PASS"

"$VAL"
ok "validator PASS"

ok "gate PASS"
