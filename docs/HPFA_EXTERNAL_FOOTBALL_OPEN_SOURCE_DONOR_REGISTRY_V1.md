# HPFA External Football Open-Source Donor Registry V1

STATUS: SUPPORT_DONOR_REGISTRY — NOT PRODUCT AUTHORITY

Verified donor references for HPFA. Adapt ideas only after current-repo false-gap, license, observability and ACTIVE_MATCH checks.

| Project | Verified URL | Role | HPFA use |
|---|---|---|---|
| socceraction | https://github.com/ML-KULeuven/socceraction | MIT; SPADL, xT/VAEP research | provider-neutral action grammar; action/state/model boundary |
| kloppy | https://github.com/PySport/kloppy | BSD-3-Clause; vendor-independent data model | boundary normalization; coordinate/orientation admission |
| StatsBomb Open Data | https://github.com/statsbomb/open-data | event schema/open examples | relations, qualifiers, set-piece/event context reference |
| StatsBombPy | https://github.com/statsbomb/statsbombpy | client/reference tooling | loader/schema research; dependency not required |
| Metrica sample-data | https://github.com/metrica-sports/sample-data | event + tracking reference | event-vs-tracking observability boundary |
| SkillCorner Open Data | https://github.com/SkillCorner/opendata | tracking/dynamic-event reference | tracking-only concept boundary; no mandatory dependency |
| LaurieOnTracking | https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking | MIT; tracking/pitch-control/EPV tutorials | negative control for event-only physical/geometric claims |

## ADAPT_NOW rules
- Normalize provider semantics at ingestion/admission boundary, not inside football constructs.
- Admit coordinate system and attacking orientation before spatial interpretation.
- Map provider event labels semantically; provider labels are not physical/tactical truth.
- xT/VAEP/EPV-like values remain model outputs with source/version/admission, never facts.
- Event coordinates do not authorize pitch-control, velocity, acceleration, team-shape, compactness or off-ball geometry claims.
- Tracking/video remain optional research surfaces and never mandatory HPFA dependencies.

## Direct-import rejection
Do not copy a donor ontology wholesale, create a parallel ingestion/sequence/phase/metric/claim engine, import opaque quality scores, or rename event proxies as tracking-derived truths.

## Promotion rule
SOURCE IDEA → CURRENT HPFA OWNER → FALSE-GAP CHECK → LICENSE CHECK → OBSERVABILITY CHECK → MINIMAL ADAPTATION → TEST → ACTIVE_MATCH EVIDENCE → RED TEAM.
