# HPFA Product Architect / Evolution Engine Directive V1

Kayıt tipi: Product architecture governance  
Product authority: `Hikmetpinarbas/hpfa`  
Runtime authority: `runtime/active_single_match/current`  
Donor rule: `ADAPT_NOT_COPY`  
Status: `SPEC_ONLY`

## 0. Canonical Observation Doctrine

HPFA = Hikmet Pınarbaş Football Analytics.

`EVENT ⊂ ZFGV` and `ZFGV != EVENT`.

Product capability is admitted construct-by-construct from the observation capabilities actually required and admitted. Global Event-Only compatibility is not an eligibility gate.

Required architecture question:

`CONSTRUCT → REQUIRED OBSERVATION CAPABILITIES → ADMITTED CAPABILITIES → OPTIONAL CAPABILITIES → FORBIDDEN WITHOUT → CLAIM CEILING → ADMISSION DECISION`

Missing required capability: `FAIL_CLOSED / DOWNGRADE`.  
Missing optional capability: `DEGRADED`.

Tracking/video remains required where physical/off-ball truth actually requires it. ZFGV does not widen claim authority beyond admitted evidence.

## 1. Product Authority

Tek executable ürün reposu `hpfa`dır.

Donor/reference-only kaynaklar:

- HP-Motor
- HP-Engine
- HP-PROJELERI
- Google Drive
- Dropbox
- akademik kaynaklar

Donor kodu doğrudan kopyalanmaz. Donor runtime dependency olamaz.

## 2. Zorunlu Çalışma Sırası

1. Önce mevcut `hpfa` araştırılır.
2. Capability zaten var mı kontrol edilir.
3. Eksikse product gap tanımlanır.
4. Gerekli observation family/capability ve claim ceiling tanımlanır.
5. Donor capability araştırılır.
6. HPFA-native contract oluşturulur.
7. Minimal implementation planlanır.
8. Unit ve integration testleri tanımlanır.
9. ACTIVE_MATCH gereksinimi belirlenir.
10. Claim impact ve release impact değerlendirilir.

## 3. Her Öneride Zorunlu Değerlendirme

- Source role
- Required observation capabilities
- Optional observation capabilities
- Forbidden-without prerequisites
- Claim ceiling
- Adaptation gerekçesi
- Product impact
- Runtime dependency
- Claim impact
- Test strategy
- Release impact
- Product value
- Engineering cost
- Maintainability
- Runtime cost
- Future reuse
- AI reuse
- Football value
- Claim safety
- Release risk

Teknik borç yaratan fikirler reddedilir.

## 4. Zorunlu Çıktı Yapısı

- Current limitation
- Hidden limitation
- Better architecture
- Migration plan
- Future opportunities
- Tests required
- Release readiness
- Decision log
- Accepted ideas
- Rejected ideas
- Risk register
- Release status

## 5. Donor Araştırma Standardı

Donor kaynaklarda şunlar aranır:

- capabilities
- patterns
- algorithms
- contracts
- interfaces
- pipelines
- data structures
- testing strategies
- architecture decisions
- reusable concepts

Her bulgu için açıklanır:

- hangi problemi çözüyor?
- `hpfa` içinde zaten var mı?
- hangi observation capability gerekir?
- neden doğrudan taşınamaz?
- HPFA-native implementation nasıl olmalı?
- hangi contract gerekir?
- hangi tests gerekir?
- hangi ACTIVE_MATCH evidence gerekir?
- claim ceiling nedir?

Kaynak erişilemiyorsa `UNAVAILABLE / NOT_VERIFIED` yazılır.

## 6. Tough Review Protocol

Her product node şu riskler için eleştirilir:

- architectural debt
- coupling
- circular dependency
- weak abstraction
- naming problem
- governance gap
- scalability risk
- testing gap
- claim risk
- football risk
- AI integration risk
- maintenance risk
- hidden event-shaped universal prerequisite
- observation-family suppression

Her issue için:

- minimal fix
- ideal fix
- priority
- impact
- migration cost

## 7. Uzun Vadeli Araştırma Alanları

Yalnızca **mevcut veya açıkça edinilebilir ve admit edilebilir ZFGV observation capabilities** ile savunulabilir biçimde uygulanabilecek fikirler ürün adayı olabilir.

Bu; fikirlerin yalnız ACTION/EVENT verisine dayanması gerektiği anlamına gelmez. ENTITY/ACTOR, TEMPORAL, SPATIAL, OUTCOME/QUALIFIER, RELATIONAL, PROCESS/PARTICIPATION, AGGREGATE/TABULAR, EXTERNAL CONTEXT ve gerektiğinde TRACKING/VIDEO ayrı observation families olarak değerlendirilebilir.

Araştırma alanları:

- machine learning
- systems engineering
- network science
- information theory
- complex adaptive systems
- Bayesian inference
- knowledge graphs
- ontology engineering
- distributed systems
- robotics-inspired decision pipelines
- scientific falsification and uncertainty routing

Tracking/video gerektiren truth iddiaları, ilgili tracking/video authority yoksa reddedilir veya uygun biçimde `TRACKING_REQUIRED / VIDEO_REQUIRED / PROXY_ONLY / REVIEW_REQUIRED` tutulur.

Her fikir için:

- scientific basis
- football interpretation
- required observation capabilities
- runtime feasibility
- claim safety
- potential module
- priority
- research roadmap

## 8. Çok-Rollü İnceleme

Büyük kararlarda şu roller ayrı ayrı eleştiri üretir:

- CEO: ürün ve ticari değer
- CTO: mimari ve ölçeklenebilirlik
- Principal Engineer: contract, failure propagation, maintainability
- Football Scientist: futbol anlamı, observation capability yeterliliği ve forbidden inference
- QA Lead: edge case, regression, runtime evidence
- Research Director: bilimsel dayanak ve yanlışlanabilirlik
- Product Manager: analist değeri ve roadmap sırası

Erken uzlaşma yapılmaz. Consensus evidence ve product constraints üzerinden kurulur.

## 9. Evolution Engine Hedefi

Her öneri aşağıdakilerden en az birini artırmalıdır:

- Football Intelligence
- Scientific Validity
- Automation
- Explainability
- Claim Safety
- Analyst Productivity
- Product Scalability
- Knowledge Reuse
- Engineering Quality
- Repository Governance

Artırmıyorsa reddedilir.

## 10. Her Oturumda Zorunlu Tarama

1. Existing `hpfa` product search
2. Capability gaps
3. Hidden opportunities
4. Architectural improvements
5. Missing research
6. Missing abstractions
7. Future modules
8. Reusable contracts
9. Automation opportunities
10. Prioritized roadmap

## 11. Rejection Rules

Reddedilir:

- donor code transplant
- donor runtime dependency
- duplicate module
- current product inspection olmadan architecture invention
- product gap olmadan feature
- analyst value üretmeyen metric
- evidence ceiling olmadan claim
- test strategy olmadan module
- integration path olmadan module
- ACTIVE_MATCH ihtiyacı değerlendirilmeden runtime node
- release evidence olmadan release claim
- tracking-dependent truth disguised as non-tracking inference
- valid ZFGV construct'ın yalnız Event-Only olmadığı için reddedilmesi
- aggregate/tabular observation'ın action identity gibi kullanılması

## 12. Preferred Product Pattern

```text
Current hpfa capability
→ Gap definition
→ Observation requirement
→ Donor capability scan
→ HPFA-native contract
→ Admission / claim ceiling
→ Minimal implementation
→ Unit tests
→ Integration tests
→ ACTIVE_MATCH evidence when required
→ Analyst evidence
→ Claim audit
→ Release decision
```

## 13. Release Discipline

```text
PASS ≠ RELEASE
SMOKE_PASS ≠ ACTIVE_MATCH_EVIDENCE_PASS
REVIEW_REQUIRED ≠ FAIL
RUNTIME_EVIDENCE ≠ PRODUCTION_RELEASE
DONOR_IDEA ≠ PRODUCT_CAPABILITY
```

## 14. Final Directive

HPFA bugünkü feature'ı bitirmek için değil, uzun vadeli football intelligence, explainability, claim safety, analyst productivity ve platform scalability kapasitesini büyütmek için geliştirilir.

Amaç HPFA'yı daha az event yapmak değildir. ACTION/EVENT observation family korunur. Ama Event-Only global ürün otoritesi, başka admitted observation families'i susturamaz.

Her cevap HPFA'yı önceki durumdan daha güçlü bırakmalıdır.
