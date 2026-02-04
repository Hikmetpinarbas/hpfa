# HP-ENGINE Metric Registry v2 (Schema)

## Required keys (top-level)
- canonical_name: str
- metric_family: str
- definition: str
- unit: str
- polarity: +1|-1|0
- status: ACTIVE|BLOCKED|DEPRECATED
- version: semver str

- data_requirements:
    required_sources: [event|tracking|physical|video|pose|manual]
    required_fields: [str...]
    optional_fields: [str...]
    minimum_granularity: action|possession|phase|match

- modes:
    FULL:
      logic_method: str
      min_confidence: float(0..1)
    DEGRADED:
      logic_method: str
      min_confidence: float(0..1)
      proxy_note: str

- lineage:
    source: str
    derivation: str
    assumptions: [str...]

- grouping:
    phase_tags: [F1..F6]
    dimension_tags: [tactical|technical|physical|psych|neuro|context]
    hierarchy_level: L1|L2|L3|L4
    entity_level: player|team|unit|pair|sequence
    time_grain: match|phase|rolling_5|rolling_10|event_window|possession|sequence|action

- aggregation:
    aggregation_levels: [player|position|team|unit]
    rollup_method: weighted_mean|sum|rate|share|max|min|null
    weight_field: str|null
    denominator: per90|per_possession|per_phase|none

- temporal_dynamics:
    phase_splits: [0-15|15-30|30-45|45-60|60-75|75-90]
    rolling_windows: [5|10|15]          # minutes
    event_windows:
      - event: goal_scored|goal_conceded|red_card|substitution
        window: [-5, +10]              # minutes

- falsifiability:
    h0: str
    h1: str|null
    supports: [canonical_name...]
    contradicts: [canonical_name...]
    min_sample: str
    confidence_floor: float(0..1)
    conflict_rule: soft|hard           # hard => claim marked CONFLICT

- context_engine:
    context_keys: [league|season|venue|opponent_tier|score_state|tactical_context]
    benchmark_model: static|contextual
    benchmark_ref: str                 # points to canon/benchmarks.yaml key
    interpretation_notes: [str...]

- viz:
    default_chart: sparkline|bar|radar|phase_stack|pitch_map|network|waterfall|table
    chart_role: compare|trend|distribution|spatial|causal_hint
    unit_format: percent|float|int|per90|zscore
    plot_data_contract:
      type: timeseries|scalar|distribution|pitch_points|pitch_grid|network_graph|waterfall
      fields: [str...]
    caption_template: str              # TV / coach caption skeleton

- evidence_policy:
    evidence_required: none|recommended|required
    evidence_types: [timestamp|clip|sequence_id|frame_range]
    evidence_generation: auto|manual|blocked