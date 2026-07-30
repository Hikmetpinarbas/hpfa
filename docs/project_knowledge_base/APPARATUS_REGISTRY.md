# HPFA Apparatus Registry

Kayıt tipi: apparatus bilgi tabanı  
Amaç: HPFA içinde konuşulan, araştırılan, tasarlanan veya product module'a dönüşen tüm apparatus adaylarını tek yerde izlemek.  
Runtime authority: Bu registry runtime truth değildir. ACTIVE_MATCH execution ayrı kanıt ister.

---

## Status Values

- `IDEA`
- `RESEARCH`
- `SPEC`
- `PROTOTYPE`
- `ACTIVE_MATCH`
- `PRODUCTION`
- `REJECTED`
- `WAITING_OPERATOR_SELECTION`

## Claim Levels

- `REFERENCE_ONLY`
- `SURFACE_EVIDENCE_ONLY`
- `CANDIDATE_ONLY`
- `PROXY_ONLY`
- `ACTIVE_MATCH_EVIDENCE`
- `PRODUCTION_BOUND`

---

## Registry Table

| Apparatus ID | Apparatus Name | Amaç | Girdi | Çıktı | Claim seviyesi | Bağımlılıklar | Durum |
|---|---|---|---|---|---|---|---|
| APP-ACTION-CHAIN-001 | Action Chain Apparatus | Event satırlarından zincir adayları üretmek | surface/event-like rows, action family labels, time/order evidence | chain candidates, transition notes | CANDIDATE_ONLY | Canonical Event Lite, Time Surface Gate, Sequence Layer | IDEA |
| APP-SECOND-BALL-001 | Second Ball Apparatus | Restart/duel/recovery sonrası ikinci top davranış adaylarını yakalamak | restart labels, duel/pressure rows, recovery rows, time/order proximity | second-ball candidate evidence | PROXY_ONLY | Time Surface Gate, Event Window Builder, Claim Gate | IDEA |
| APP-CONSEQUENCE-001 | Consequence Apparatus | Aksiyon sonrası visible outcome ilişkilerini kurmak | action family, terminal actions, losses, recoveries, shots | consequence candidates | CANDIDATE_ONLY | Event State Transition Verifier, Time Surface Gate | RESEARCH |
| APP-EVENT-WINDOW-001 | Event Window Apparatus | Full-match volume yerine zaman penceresi adayları üretmek | surface rows, minute/time evidence, action-family counts | event window candidates | SURFACE_EVIDENCE_ONLY | Minimum Viable Context, Time Surface Gate | PROTOTYPE |
| APP-CONTEXT-001 | Context Apparatus | Claim-safe yorumdan önce minimum bağlam üretmek | surface inventory, score/time/team evidence if available | context candidates | CANDIDATE_ONLY | Minimum Viable Context, Claim Gate | PROTOTYPE |
| APP-MOMENTUM-001 | Momentum Apparatus | Event-only momentum adayları üretmek | event windows, action-family changes, terminal pressure, recovery/loss density | momentum candidates | PROXY_ONLY | Event Window Builder, Time-Scale Router, Sequence Layer | IDEA |
| APP-ENTROPY-001 | Entropy Apparatus | Action-family/zone/channel dağılım çeşitliliği üzerinden davranış çeşitliliği adayı üretmek | action-family counts, zone/channel counts, windows | entropy/variation signals | PROXY_ONLY | Metric Primitive Lite, Event Window Builder | IDEA |
| APP-PHASE-001 | Event-derived Phase State | Doğrulanmış event kanıtından claim-gated faz segmentleri üretmek | PR #205 visible sequences, action families, time/team continuity, direction-normalized zones | phase segments, cross-team transition context windows | CANDIDATE_ONLY | PR #205, Event Identity Gate, Claim Gate | SPEC_AND_TESTED_IMPLEMENTATION / PR #206 / ACTIVE_MATCH_NOT_EVALUATED |
| APP-ONTOLOGY-001 | Ontology Apparatus | Event, primitive, sequence, behaviour, pattern ve identity kavramlarını standartlaştırmak | action vocabulary, donor concepts, product contracts | ontology registry | REFERENCE_ONLY | HP-Motor donor, HP-Engine donor, HP-PROJELERI governance | RESEARCH |
| APP-STYLE-DETECTION-001 | Style Detection Apparatus | Repeated visible event-surface patterns üzerinden style candidate üretmek | pattern candidates, windows, team labels, action-family distribution | style candidates | CANDIDATE_ONLY | Pattern Grammar, Claim Gate, ACTIVE_MATCH validation | IDEA |
| APP-SEQUENCE-001 | Visible Action Sequence Candidate Admission | Zaman katmanı, takım devamlılığı ve boundary kanıtından görünür sequence adayları üretmek | selected action/event consequence surfaces, ordered time layers | visible sequence candidates, boundaries, trace signals | CANDIDATE_ONLY | PR #203, time-layer gate, claim gate | CURRENT_HEAD_CI_SUCCESS / PR #205 / ACTIVE_MATCH_EXECUTION_REVIEW_REQUIRED / NOT_MERGED |
| APP-RESPONSE-001 | Response Apparatus | Bir aksiyon/olay sonrası takımın visible response adayını yakalamak | event windows before/after trigger, action-family deltas | response candidates | PROXY_ONLY | Event Window Builder, Consequence Apparatus, Claim Gate | IDEA |

---

## Apparatus Entry Template

```text
Apparatus ID:
Name:
Amaç:
Girdi:
Çıktı:
Claim seviyesi:
Bağımlılıklar:
Durum:
Donor basis:
ACTIVE_MATCH requirement:
Analyst-facing value:
Red-team risk:
Next step:
```

---

## Registry Rules

1. Apparatus konuşulduğu anda kayda girebilir; product module sayılmaz.
2. `IDEA` veya `RESEARCH` durumundaki apparatus için runtime claim kurulmaz.
3. `ACTIVE_MATCH` durumuna geçmek için gerçek `runtime/active_single_match/current` execution gerekir.
4. `PRODUCTION` için contract, tests, runtime evidence, claim boundary ve football output audit gerekir.
5. Apparatus doğrudan metrik değildir; futbol davranışı keşfetme kapasitesi üretmelidir.
6. Yeni apparatus yalnızca yeni bilgi üretirse veya mevcut bilgiyi belirgin iyileştirirse tutulur.
