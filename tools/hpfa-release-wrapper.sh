#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
REPO="${HPFA_REPO:-$HOME/hpfa}"
exec "$REPO/tools/hpfa-release.sh" "$@"
