# HP-ENGINE METRIC REGISTRY SCHEMA v1

Each metric entry MUST include:

- canonical_name: string
- metric_family: string
- definition: string
- unit: string
- polarity: +1|-1|0
- data_requirements:
  - required_sources: list (event|tracking|physical|video|manual)
  - required_fields: list
- modes:
  - FULL:
      logic_method: string (function id)
      min_confidence: float
  - DEGRADED:
      logic_method: string (function id or proxy id)
      min_confidence: float
      proxy_note: string
- lineage:
  - source: string
  - derivation: string
- tests:
  - sanity_checks: list[string]
- version: string (SemVer)
- status: ACTIVE|BLOCKED|DEPRECATED