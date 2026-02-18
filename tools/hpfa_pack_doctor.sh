#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

HOME="/data/data/com.termux/files/home"
REPO="$HOME/hpfa"
PACK="$HOME/HP_ARCHIVES/_PACKED"
DIAG="$REPO/_diag"
LOG="$DIAG/pack_verify_last.log"

mkdir -p "$DIAG"

if [ ! -d "$PACK" ]; then
  echo "[FAIL] PACK dir missing: $PACK" >&2
  exit 2
fi

cd "$PACK"

{
  echo "HPFA PACK DOCTOR v3 (subdir-aware)"
  echo "ts=$(date -Iseconds)"
  echo "pack=$PACK"
  echo "----------------------------------------"

  mapfile -t sha_files < <(find . -type f -name '*.sha256' -print | sort)
  echo "[INFO] sha256 files found=${#sha_files[@]}"

  if [ "${#sha_files[@]}" -eq 0 ]; then
    echo "[FAIL] no .sha256 files found anywhere under: $PACK"
    exit 10
  fi

  echo "[INFO] sample sha256 files:"
  printf '%s\n' "${sha_files[@]}" | sed -n '1,60p'
  echo "----------------------------------------"

  bad=0
  missing=0
  mismatch=0

  for f in "${sha_files[@]}"; do
    echo ">>> VERIFY: $f"
    out="$(sha256sum -c "$f" 2>&1 || true)"
    echo "$out"

    m1="$(echo "$out" | grep -E 'No such file|cannot open' | wc -l | tr -d ' ')"
    m2="$(echo "$out" | grep -E 'FAILED$' | wc -l | tr -d ' ')"
    miss=$((miss + 0)) 2>/dev/null || true

    if [ "$m1" != "0" ]; then missing=$((missing + m1)); fi
    if [ "$m2" != "0" ]; then mismatch=$((mismatch + m2)); fi

    # any non-OK lines count as bad
    b="$(echo "$out" | grep -v 'OK$' | wc -l | tr -d ' ')"
    if [ "$b" != "0" ]; then bad=$((bad + b)); fi

    echo
  done

  echo "----------------------------------------"
  echo "[SUMMARY] bad=$bad missing=$missing mismatch=$mismatch"

  if [ "$bad" = "0" ]; then
    echo "[PASS] PACK sha256 all OK"
  else
    echo "[FAIL] PACK sha256 invalid"
  fi

} | tee "$LOG"

if rg -n '^\[PASS\] PACK sha256 all OK' "$LOG" >/dev/null 2>&1; then
  exit 0
fi
exit 1
