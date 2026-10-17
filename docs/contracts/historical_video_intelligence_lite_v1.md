# HPFA Historical Video Intelligence Lite V1 Contract

Date: 2026-10-17

Status: `SPEC_AND_EXECUTABLE_CANDIDATE_NOT_RELEASED`

Module: `hpfa/modules/core/historical_video_intelligence_lite/`

Colab: `notebooks/hpfa_historical_video_intelligence_colab_v1.ipynb`

## Purpose

Turn match video into time-stamped, rights-checked, evidence-classed event rows that the existing HPFA spine can ingest — without promoting detector output to event truth and without producing tracking statistics.

```text
VIDEO (rights manifest PASS)
→ Stage A triage (compressed-domain, whole video, no decoding)
→ windows = triage windows ∪ seeded random audit windows
→ Stage B detail (decode windows only)
→ event CANDIDATE rows (DERIVED_OBSERVATION)
→ verification: independent reference labels | named human review
→ VERIFIED_* rows → hpfa_surface/video_event_surface_verified_v1.csv
→ csv_surface_reader_lite (existing HPFA reader)

COUNTERFACTUAL ("if played today") — separate file, separate layer, consumes
verified ids by reference, never edits observed rows.
```

Within ZFGV, video is one observation surface. This module supplies the observation capability for visible restarts and goal-restart patterns; it does not supply ball trajectory, player identity or 22-player geometry.

## Source and rights gate (`rights_gate.py`)

Processing requires a manifest with:

| field | admissible values |
|---|---|
| `rights_status` | `OPEN_LICENSE` (needs `license` + `license_url`), `LICENSED`, `OPERATOR_ATTESTED_LAWFUL_ACCESS` (needs `attestation`) |
| `acquisition_method` | anything except `UNKNOWN`, `DRM_CIRCUMVENTION`, `DOWNLOAD_PROTECTION_BYPASS`, `STREAM_RIPPING_WITHOUT_PERMISSION`, `ACCOUNT_OR_GEO_RESTRICTION_BYPASS` |
| `download_protection_circumvented` | must be exactly `false` |
| `publication_cleared` | separate flag; processing permission is never publication permission |

`UNKNOWN`, `REVIEW_REQUIRED`, `NOT_CLEARED` → `FAIL_CLOSED` before any frame is decoded. The gate records `legal_determination_made=false`: it checks that a basis was recorded, it does not decide legality. The module contains no platform downloader.

## Two-stage processing (`stages.py`)

**Stage A — triage.** Reads video packet sizes from the container (`ffprobe`, no decode). Inter-frame bytes per second is a proxy for visible change. Low-activity runs relative to a rolling in-play reference (75th percentile, 180 s) are dead-ball candidates; their ends define triage windows (`[end−12 s, end+8 s]`). Optional extra triage reasons: audio energy peaks, broadcast cuts (decoded keyframes). Coverage is capped (`max_triage_fraction`).

**Random audit.** A seeded uniform sample of 30 s slots (`random_fraction`, default 8%) is always added. Because the sample is independent of the triage signal, `share of reference events inside audit windows that are also inside triage windows` is an unbiased estimate of triage recall on footage without labels. The validation report prints it next to the true value.

**Stage B — detail.** Decodes only windows (default 5 fps, 384 px), computes camera-shift-compensated pixel activity, pools an in-play reference across all windows of the video, and emits:

| detector | event | time | basis |
|---|---|---|---|
| `restart_after_dead_ball_v1` | `SET_PIECE_RESTART` (type `UNKNOWN`) | activity onset after a low run | visible activity pattern |
| `goal_by_long_stoppage_then_restart_v1` | `GOAL` (subtype `INFERRED_FROM_RESTART_PATTERN`) | start of a long stoppage | celebration + kick-off pattern; indirect |
| `audio_salience_peak_v1` | `SHOT` (`AUDIO_SALIENCE_PROXY`) | audio peak − 2 s | crowd/commentary reaction; indirect |

No detector exists for `BALL_RECOVERY`, typed restarts (`FREE_KICK`, `THROW_IN`, `CORNER_KICK`, `KICK_OFF`) or direct shot observation: they stay `NOT_SUPPORTED`. A restart row gets a type only from a reference label or a human reviewer.

## Event row contract (`hvi_contract.py`)

Required fields: `event_id, layer, source_video_id, source_fingerprint, rights_manifest_id, period, video_time_s, video_time_end_s, video_timestamp, time_uncertainty_s, match_clock, event_type, event_subtype, team, team_basis, player, player_basis, detector_id, stage, score, score_basis, confidence_bound, evidence_kind, verification_status, verification_basis, capability_status, claim_ceiling`.

Rules enforced by `validate_event`:

- `team`/`player` ≠ `UNKNOWN` requires a basis (reference side label, reference player id, or human review). Side labels are not identity.
- `VERIFIED_*` requires `verification_basis` (reference id + time delta, or reviewer name).
- any `tracking_*`, `distance_m`, `speed_kmh`, `pitch_control` field is a contract violation.
- `score` is an uncalibrated detector rank (`score_basis=UNCALIBRATED_DETECTOR_SCORE_NOT_PROBABILITY`). Confidence bounds are the Wilson 95% intervals of held-out precision/recall for that event type and domain.
- `match_clock=UNKNOWN` unless a clock alignment is admitted. `source_fingerprint` is a sampled content hash (size + first/middle/last 4 MiB), not a full-file hash.

## HPFA surface projection (`hpfa_export.py`)

`hpfa_surface/video_event_surface_verified_v1.csv` holds `VERIFIED_*` rows only, with columns the existing reader resolves: `team, event_type, subtype, period, start_time_s, end_time_s` (+ provenance columns). Mapping:

| video event | `event_type` | `subtype` | reader family |
|---|---|---|---|
| `SHOT` | `SHOT` | | `shot` |
| `SET_PIECE_RESTART` (untyped) | `SET PIECE` | `UNKNOWN` | ambiguous (by design) |
| restart typed by reference/human | `SET PIECE` | `THROW IN` / `FREE KICK` / `CORNER KICK` / `KICK OFF` | restart family |
| `GOAL` | `GOAL` | | `UNKNOWN_ACTION` (reader has no goal family) |
| `BALL_RECOVERY` | `RECOVERY` | | `recovery` |

Candidates go to `video_events_v1.json` and the review queue `video_event_review_queue_v1.tsv` (`decision ∈ CONFIRM/REJECT/RELABEL`, `reviewer` mandatory). The file name avoids `team`/`player`/`match` tokens so inventory role inference gives `EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE`.

## Validation and capability admission (`evaluation.py`, `calibration.py`, `validate_dataset.py`, `report.py`)

- Reference adapter: BAS format (`gameTime`, `position` ms, `label`, `team`). Unknown labels fail loudly. `Player Successful Tackle → BALL_RECOVERY` is marked `PARTIAL_TACKLE_WIN_ONLY`. Restart references = `Free Kick`, `Throw In`, first labelled touch ≤ 60 s after `Out` (goal kick / corner), first touch ≤ 180 s after `Goal` (kick-off).
- Matching: greedy one-to-one, highest score first, per-type tolerance (restart 5 s, goal 15 s, shot 3 s) plus a 1/2/5/10 s sweep.
- Calibration: grid search of Stage B thresholds on cached series of **one** half; numbers from it are labelled in-sample.
- Held-out: other matches, calibrated settings frozen. Pooled TP/FP/FN, precision/recall with Wilson 95% CI, FP per video-hour, triage recall (true and random-audit estimate).
- Admission policy: `SUPPORTED_IN_VALIDATED_DOMAIN` if ≥ 10 references and Wilson lower bounds of precision and recall ≥ 0.5; `EXPERIMENTAL` if point precision and recall ≥ 0.3; else `NOT_SUPPORTED`. Policy, not truth; thresholds are parameters.
- Domain rule: a capability file carries `validated_domain`; on any other domain `SUPPORTED` is capped at `EXPERIMENTAL`.

## Measurement

Every run writes `video_run_report_v1.json` with: native fps/resolution/size, Stage A signal and effective sample rate, Stage B fps/width/frames, triage/audit/Stage B coverage fractions, wall time, CPU (Python and ffmpeg children), peak RSS, real-time factor, host (CPU count, GPU, Colab flag).

## Counterfactual layer (`counterfactual_layer.py`)

`layer=COUNTERFACTUAL_MODEL_LAYER`, `evidence_kind=HYPOTHESIS` unless a registered model with `validation_status=VALIDATED` is supplied; explicit assumptions are mandatory; input must be observed-layer rows and only verified ids are referenced; writing into `hpfa_surface/` is refused.

## Claim boundary

```text
canonical_event_count=UNKNOWN
tracking_data_available=false
tracking_statistics_emitted=false
validated_team_identity=false
validated_player_identity=false
detector_score_is_probability=false
domain_transfer_admitted=false
counterfactual_mixed_with_observation=false
production_release=false
```

Does not measure: tracking statistics, distance, speed/physical load, pitch control, team shape/compactness, pressing intensity, possession share, pass network, tactical intention, causal effect.
