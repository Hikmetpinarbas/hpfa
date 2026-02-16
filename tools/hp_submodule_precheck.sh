#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

URL="${1:-}"
if [ -z "$URL" ]; then
  echo "[FAIL] usage: hp_submodule_precheck.sh https://github.com/user/repo.git"
  exit 2
fi

# hard fail if repo doesn't exist (HEAD request)
if command -v curl >/dev/null 2>&1; then
  code="$(curl -s -o /dev/null -w '%{http_code}' -L "$URL" || true)"
  # github returns 404 for missing repo (or 200/301 for existing)
  if [ "$code" != "200" ] && [ "$code" != "301" ] && [ "$code" != "302" ]; then
    echo "[FAIL] repo not reachable (HTTP $code): $URL"
    exit 11
  fi
else
  echo "[WARN] curl missing; install: pkg install curl"
  echo "[FAIL] cannot verify repo existence without curl"
  exit 12
fi

echo "[OK] repo reachable: $URL"
