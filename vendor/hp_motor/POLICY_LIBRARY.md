# HP-MOTOR Library Policy (v1)

## Purpose
Keep the repository lean and reproducible on Termux/Android.
Avoid uncontrolled growth, duplicates, and accidental commits of heavy inputs.

## Canonical roles (source of truth)
- `hp_motor/library/inputs/drive_hp_proj_docs/`
  - Canonical home for documents/research (`.pdf`, `.docx`, `.txt`, `.md`)
  - This is where docs should live after import routing.

- `hp_motor/library/inputs/drive_hp_proj_packages/`
  - Canonical home for packages (`.zip`, `.7z`, `.rar`)

- `hp_motor/library/inputs/drive_hp_proj_other/`
  - Uncategorized leftovers (review periodically)

- `hp_motor/library/inputs/drive_hp_proj/`
  - INBOX only (temporary staging).
  - Do not keep docs here. Run import routing to place files in canonical folders.

## Workflow
1) Drop new files into `drive_hp_proj/` (INBOX).
2) Run import routing (dry-run first):
   - `python tools/import_drive_bundle.py --src hp_motor/library/inputs/drive_hp_proj`
3) If routes look correct, apply:
   - `python tools/import_drive_bundle.py --src hp_motor/library/inputs/drive_hp_proj --apply`
4) Keep INBOX small:
   - After successful import, remove duplicates from INBOX (prefer quarantine first).

## Safety rules (non-negotiable)
- Never delete without a reversible step:
  - quarantine -> validate -> then delete
- Never commit heavy inputs:
  - `data/`, `hp_motor/library/inputs/`, `hp_motor/library/registry/inputs/`, `tools/_scratch/` stay local.
- If something must be versioned, whitelist it explicitly (small fixtures only).

