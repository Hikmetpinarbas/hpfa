# HPFA Independent Repository Consolidation Audit

## 1. Missing Repositories and Access
This is a read-only consolidation assessment for the following repositories. Note the accessibility inside this environment:
* **Hikmetpinarbas/hpfa**: Fully accessible (Current Repository).
* **Hikmetpinarbas/HP-Engine**: Accessible locally under `vendor/hp_engine`.
* **Hikmetpinarbas/HP-Motor**: Accessible locally, cloned to `vendor/hp_motor_cloned`.
* **Hikmetpinarbas/HP-Motor-main**: **Not Accessible** (HTTP 404). Contains PRIVATE HPA code.
* **Hikmetpinarbas/HIO-Analytics**: **Not Accessible** (HTTP 404).
* **Hikmetpinarbas/YelFootballLab**: **Not Accessible** (HTTP 404).

## 2. Baseline and Branch Analysis
* **hpfa Active Development Baseline**: The current active development branch is `origin/postclosure/analyst-explanation-v1-20261005` (commit `7c5ffe5`).
* **Relationship to main**: `origin/main` is currently on commit `7648b16` (dated Sep 21 2026). Active development is significantly ahead of `main` via various integration, repair, and feature branches (e.g., `commercial-pilot-readiness-20261005`, `release-readiness-20261004`). Main should not be assumed to be the latest development baseline.

## 3. Inventory of Accessible Repositories
### `hpfa`
* **Python Modules**: Over 50 `_lite` components in `hpfa/modules/core/` (e.g., `active_match_spine_runner.py`, `evidence_atom_inventory_lite`, `canonical_event_lite`). Root wrapper scripts like `active_match_full_run.py`.
* **Tests**: `tests/` directory and `.github/workflows/` with over 100 CI checks.
* **Dependencies**: `pandas`, `pytest`, `streamlit`

### `HP-Engine` (`vendor/hp_engine`)
* **Python Modules**: `engine/hp_engine_*.py` suite, `engine/metrics/` and `engine/metrics_impl/` (encyclopedia of tactical metrics like `field_tilt`, `ppda`), `engine/ingest/sportsbase_csv.py`.
* **Tests**: `run_test.py`
* **Dependencies**: `pandas`, `numpy`, `plotly`, `matplotlib`, `mplsoccer`, `scipy`, `pdfplumber`, `python-docx`, `ultralytics`, `opencv-python-headless`, `kloppy`, `socceraction`, `scikit-learn`, `networkx`, `openpyxl`, `pyyaml`, `pytest`, `streamlit`.
* **Entry Points**: `streamlit_app.py`, `engine/cli/inspect_file.py`, `engine/master_orchestrator.py`.

### `HP-Motor` (`vendor/hp_motor_cloned`)
* **Python Modules**: Procedural pipeline steps (`STEP12_PHASE_TAGGER_MVP.py`, `STEP13_TEMPO_MOMENTS.py`, `STEP14_BRIEF_V2_RENDER.py`).
* **Tests**: `tests/` directory present.
* **Dependencies**: `PyYAML`, `pytest`, `pandas`, `openpyxl`.
* **Entry Points**: `run_hp_motor.py`, `run_hp_pipeline.py`, `hp_guardrail_cli.py`.

## 4. Duplicated Implementations and Conflicts
* **Duplications**: Both `hpfa` and `HP-Engine` have CSV ingestion mechanisms (`csv_surface_reader_lite.py` vs `engine/ingest/csv_ingest.py` / `sportsbase_csv.py`). Reporting is split across `hpfa` (`active_match_analyst_report_lite.py`), `HP-Engine` (`streamlit_app.py`), and `HP-Motor` (`STEP14_BRIEF_V2_RENDER.py`).
* **Conflicts**: `hpfa` enforces a strict "claim-safe, event-only, no-guessing" ontology (Row Nucleus -> Evidence Atom). In contrast, `HP-Motor` introduces tagging and tempo guessing (`PHASE_TAGGER_MVP`, `TEMPO_MOMENTS`), which may violate `hpfa`'s evidence-only safety locks.
* **Import Paths**: `HP-Engine` uses absolute internal imports (e.g. `engine.metrics`), while `hpfa` is structured under `hpfa.modules.core`. `HP-Motor` relies heavily on standalone flat scripts and Termux-specific directory assumptions (`MATCH_PACK/out`).

## 5. Modules Already Present in `hpfa`
* Core evidence adapters and foundational structures: `csv_surface_reader_lite.py`, `xml_surface_reader_lite.py`, `metric_family_registry.py`, `provider_alias_field_semantics_lite.py`, `active_match_spine_runner.py`.

## 6. Proposed Clean Modular Repository Tree
```
hpfa/
├── core/
│   ├── evidence/         (surface readers, evidence atoms, provenance guards)
│   ├── prematch/         (scouting, opposition profile generation)
│   ├── postmatch/        (active match runner, sequence reconstruction)
│   ├── video/            (video scope policy, synchronization, title lexicons)
│   ├── scouting/         (player profiling, metric translation)
│   └── broadcast/        (graphics pack, visual storytelling)
├── tools/                (guardrails, local pipeline runners)
└── tests/                (provenance and lock regressions)
```

## 7. Migration Dependency Graph & Task List
**Dependency Graph:**
`Evidence Adapters (HP-Engine)` -> `hpfa/core/evidence` -> `Metrics Definitions (HP-Engine)` -> `hpfa/core/postmatch` -> `Reporting Steps (HP-Motor)` -> `hpfa/core/postmatch/reporting`

**Prioritized Task List (Independent Work Packages):**
1. **WP1 (Claude Code / Jules)**: Port `HP-Engine` provider semantics and metric definitions (`ppda`, `field_tilt`) into `hpfa/core/evidence`, applying `ADAPT_NOT_COPY` to ensure no labels are promoted beyond evidence.
2. **WP2 (Copilot)**: Refactor `HP-Motor` steps (`STEP12`, `STEP13`, `STEP14`) into modular `hpfa/core/postmatch` components. Strip all Termux-hardcoded paths.
3. **WP3 (Gemini CLI)**: Unify CSV ingestion. Deprecate `HP-Engine` ingest scripts in favor of `hpfa`'s canonical `csv_surface_reader_lite.py`.
4. **WP4 (All)**: Define final `active_match_spine_runner.py` integrations for new metrics.
5. **WP5 (All)**: Remove `vendor/hp_engine` and deprecated repos.

## 8. Risks: Licensing, Privacy, Secrets, Git History
* **Privacy**: `HP-Motor-main` is private and must not be pushed or copied to `hpfa`.
* **Secrets**: `HP-Motor`'s `alias_map.example.json` and legacy scripts might contain internal server paths or Termux environment expectations.
* **Git History**: Blindly merging `HP-Engine` or `HP-Motor` could pollute the clean provenance of `hpfa`. Code must be manually adapted (`REHABILITATE_BEFORE_PARALLEL_ENGINE`) rather than merged to keep git history clean and audit-friendly.

## 9. Acceptance Tests Definition
* Acceptance tests must run against real-match data (`MATCH_PACK/events.csv`).
* **Condition 1**: `canonical_event_count` MUST equal the distinct upstream source facts. Tests must fail if CSV/XML reflections are double-counted.
* **Condition 2**: Output analysts reports must preserve exact trace cohort provenance.
* **Condition 3**: `FAIL_CLOSED` logic must trigger when missing outcome or context semantics attempt to leak into metric models.
