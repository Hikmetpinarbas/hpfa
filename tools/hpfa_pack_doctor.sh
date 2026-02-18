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

# Collect sha256 manifests (subdir-aware)
mapfile -t sha_files < <(find "$PACK" -type f -name '*.sha256' -print | sort)

{
  echo "HPFA PACK DOCTOR v4 (subdir-aware, full-scan)"
  echo "ts=$(date -Iseconds)"
  echo "pack=$PACK"
  echo "----------------------------------------"
  echo "[INFO] sha256 files found=${#sha_files[@]}"
  if [ "${#sha_files[@]}" -eq 0 ]; then
    echo "[FAIL] no *.sha256 found under $PACK"
    echo "[HINT] expected: tar.gz(.sha256) manifests inside PACK_* dirs"
    exit 10
  fi
  echo "[INFO] sample sha256 files:"
  printf '%s\n' "${sha_files[@]}" | sed -n '1,50p'
  echo "----------------------------------------"

  bad_lines=0
  file_fail=0

  for f in "${sha_files[@]}"; do
    echo ">>> VERIFY: $f"
    out="$(sha256sum -c "$f" 2>&1 || true)"
    echo "$out"

    # Count non-OK lines for this manifest
    b="$(echo "$out" | grep -v 'OK$' | wc -l | tr -d ' ')"
    if [ "$b" != "0" ]; then
      bad_lines=$((bad_lines + b))
      file_fail=$((file_fail + 1))
    fi
    echo
  done

  echo "----------------------------------------"
  echo "[SUMMARY] manifests=${#sha_files[@]} failed_manifests=$file_fail bad_lines=$bad_lines"

  if [ "$bad_lines" = "0" ]; then
    echo "[PASS] PACK sha256 all OK"
  else
    echo "[FAIL] PACK sha256 has issues"
  fi
} | tee "$LOG"

if rg -n '^\[PASS\] PACK sha256 all OK$' "$LOG" >/dev/null 2>&1; then
  exit 0
fi
exit 1
