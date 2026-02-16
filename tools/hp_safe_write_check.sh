#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

F="${1:?usage: hp_safe_write_check.sh /path/to/file.(py|sh)}"
if [ ! -f "$F" ]; then
  echo "[FAIL] missing file: $F"
  exit 2
fi

# Shebang sanity (only for scripts)
if head -n 1 "$F" | grep -q '^#!' ; then
  :
else
  echo "[WARN] missing shebang: $F"
fi

case "$F" in
  *.py)
    python -m py_compile "$F" && echo "[OK] py_compile pass: $F"
    ;;
  *.sh)
    bash -n "$F" && echo "[OK] bash -n pass: $F"
    ;;
  *)
    echo "[WARN] unknown extension, no syntax check: $F"
    ;;
esac

# Control chars
if LC_ALL=C grep -nP "[\x00-\x08\x0B\x0C\x0E-\x1F]" "$F" >/dev/null 2>&1; then
  echo "[FAIL] control character(s) detected in: $F"
  LC_ALL=C grep -nP "[\x00-\x08\x0B\x0C\x0E-\x1F]" "$F" | head -n 20
  exit 3
fi

# CRLF detect
if LC_ALL=C grep -n $'\r' "$F" >/dev/null 2>&1; then
  echo "[FAIL] CRLF detected (\\r) in: $F"
  LC_ALL=C grep -n $'\r' "$F" | head -n 20
  exit 5
fi

# suspicious literal "\>" copy artefact
if grep -nE '^[[:space:]]*\\>' "$F" >/dev/null 2>&1; then
  echo "[FAIL] suspicious literal '\\>' lines detected in: $F"
  grep -nE '^[[:space:]]*\\>' "$F" | head -n 20
  exit 4
fi

echo "[OK] safe_write_check pass: $F"
