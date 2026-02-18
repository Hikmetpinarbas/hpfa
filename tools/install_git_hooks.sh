#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"
HOOKS="$REPO/.git/hooks"
GATE="$REPO/tools/hpfa_gate.sh"

[ -d "$HOOKS" ] || { echo "[FAIL] not a git repo: $REPO" >&2; exit 2; }
[ -x "$GATE" ] || { echo "[FAIL] gate missing: $GATE" >&2; exit 2; }

cat > "$HOOKS/pre-push" <<EOF2
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
"$GATE"
EOF2

chmod +x "$HOOKS/pre-push"

echo "[OK] installed: $HOOKS/pre-push"
