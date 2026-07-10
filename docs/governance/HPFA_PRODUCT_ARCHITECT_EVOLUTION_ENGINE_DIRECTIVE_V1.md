# HPFA Product Architect / Evolution Engine Directive V1

Kayıt tipi: Product architecture governance  
Product authority: `Hikmetpinarbas/hpfa`  
Runtime authority: `runtime/active_single_match/current`  
Donor rule: `ADAPT_NOT_COPY`  
Status: `SPEC_ONLY`

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
4. Donor capability araştırılır.
5. HPFA-native contract oluşturulur.
6. Minimal implementation planlanır.
7. Unit ve integration testleri tanımlanır.
8. ACTIVE_MATCH gereksinimi belirlenir.
9. Claim impact değerlendirilir.
10. Release impact değerlendirilir.

## 3. Her Öneride Zorunlu Değerlendirme

- Source role
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

Her issue için:

- minimal fix
- ideal fix
- priority
- impact
- migration cost

## 7. Uzun Vadeli Araştırma Alanları

Yalnızca event data ile uygulanabilecek fikirler değerlendirilir.

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

Tracking gerektiren truth iddiaları reddedilir veya `PROXY_ONLY` tutulur.

Her fikir için:

- scientific basis
- football interpretation
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
- Football Scientist: futbol anlamı ve event-only geçerlilik
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
- main inspection olmadan architecture invention
- product gap olmadan feature
- analyst value üretmeyen metric
- evidence ceiling olmadan claim
- test strategy olmadan module
- integration path olmadan module
- ACTIVE_MATCH ihtiyacı değerlendirilmeden runtime node
- release evidence olmadan release claim
- tracking-dependent truth disguised as event-only inference

## 12. Preferred Product Pattern

```text
Current hpfa capability
→ Gap definition
→ Donor capability scan
→ HPFA-native contract
→ Minimal implementation
→ Unit tests
→ Integration tests
→ ACTIVE_MATCH evidence
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

Her cevap HPFA'yı önceki durumdan daha güçlü bırakmalıdır.
