#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

BRC="$HOME/.bashrc"
BK="$HOME/.bashrc.BAK_$(date +%Y%m%d_%H%M%S)"
cp -f "$BRC" "$BK"
echo "[OK] backup=$BK"

# Goal:
# - keep only ONE occurrence of:
#   [ -f "$HOME/.config/hpfa/helpers.sh" ] && source "$HOME/.config/hpfa/helpers.sh"
# - keep only ONE interactive-shell gate (case $- in ... esac) IF it directly precedes HPFA source block
#
# Strategy:
# - stream through file
# - when we see an HPFA source line, emit it only once
# - suppress duplicate copies, and also suppress immediately preceding duplicate gate block

awk '
  function is_gate_start(line){ return line ~ /^case[[:space:]]+\$-[[:space:]]+in[[:space:]]*$/ }
  function is_gate_end(line){ return line ~ /^esac[[:space:]]*$/ }
  function is_hpfa_source(line){
    return line ~ /^\[ -f "\$HOME\/\.config\/hpfa\/helpers\.sh" \][[:space:]]+&&[[:space:]]+source "\$HOME\/\.config\/hpfa\/helpers\.sh"[[:space:]]*$/
  }

  BEGIN{
    seen_source=0
    # buffer for a possible gate block to decide later
    buffering_gate=0
    gate_buf=""
  }

  {
    line=$0

    # If buffering a gate, keep accumulating until esac
    if (buffering_gate==1){
      gate_buf = gate_buf line "\n"
      if (is_gate_end(line)){
        buffering_gate=0
        # Do not print yet; we will print only if we later keep an HPFA source after it
        pending_gate=1
      }
      next
    }

    # Detect start of interactive gate
    if (is_gate_start(line)){
      buffering_gate=1
      gate_buf = line "\n"
      next
    }

    # If this is the HPFA source line:
    if (is_hpfa_source(line)){
      if (seen_source==0){
        # print gate if it was pending
        if (pending_gate==1){
          printf "%s", gate_buf
          pending_gate=0
          gate_buf=""
        }
        print line
        seen_source=1
      } else {
        # drop duplicates (and also drop pending gate if any)
        pending_gate=0
        gate_buf=""
      }
      next
    }

    # Normal line:
    # If we had a pending gate but then encountered other content, flush gate (it was not tied to HPFA)
    if (pending_gate==1){
      printf "%s", gate_buf
      pending_gate=0
      gate_buf=""
    }

    print line
  }

  END{
    # flush any pending gate at EOF
    if (pending_gate==1){
      printf "%s", gate_buf
    }
  }
' "$BK" > "$BRC"

bash -n "$BRC" && echo "[OK] bashrc lint pass" || { echo "[FAIL] bashrc lint fail"; exit 3; }

echo "[INFO] hpfa helpers source occurrences:"
grep -nF '[ -f "$HOME/.config/hpfa/helpers.sh" ] && source "$HOME/.config/hpfa/helpers.sh"' "$BRC" || true
