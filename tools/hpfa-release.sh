#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

cat >&2 <<'MSG'
[BLOCKED] Legacy HPFA release command is disabled.
Reason: it could create/move tags and push release state outside current release governance.

Use the read-only release readiness audit instead:
  python tools/hpfa_release_readiness_audit_v1.py --repo . --wheel <wheel> --out-dir <audit-dir>

A real release requires explicit user approval plus a separately governed release action.
MSG
exit 64
