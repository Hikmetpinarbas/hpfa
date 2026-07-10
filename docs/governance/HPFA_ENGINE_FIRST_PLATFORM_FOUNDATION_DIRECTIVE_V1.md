# HPFA Engine-First Platform Foundation Directive V1

Kayıt tipi: Product architecture directive  
Product authority: `Hikmetpinarbas/hpfa`  
Runtime authority: `runtime/active_single_match/current`  
Status: `SPEC_ONLY`

---

## 1. North Star

HPFA ileride web sitesi, mobil aplikasyon, masaüstü arayüzü veya servis katmanı olarak sunulabilir.

Ancak bugünkü öncelik kullanıcı arayüzü değildir.

Öncelik:

```text
ham event yüzeyi
→ güvenilir ingest
→ canonical action candidates
→ metric primitives
→ context
→ evidence
→ claim-safe football intelligence
→ deterministic report output
```

Web ve aplikasyon katmanları daha sonra bu çekirdeği tüketen ince client'lar olacaktır.

HPFA'nın ürün değeri arayüzde değil, çekirdek analiz motorunun doğruluğunda, açıklanabilirliğinde, tekrar üretilebilirliğinde ve claim safety disiplinindedir.

---

## 2. Engine-First Principle

Aşağıdaki sıra değiştirilemez:

```text
ENGINE
→ CONTRACTS
→ TESTS
→ ACTIVE_MATCH EVIDENCE
→ STABLE OUTPUTS
→ SERVICE BOUNDARY
→ API
→ WEB / MOBILE CLIENTS
```

Arayüz, eksik veya kararsız motor davranışını gizlemek için kullanılmayacaktır.

UI geliştirmesi şu koşullar sağlanmadan başlamamalıdır:

- canonical input/output contracts stabilize edilmeden,
- runtime status dictionary stabilize edilmeden,
- claim eligibility davranışı stabilize edilmeden,
- analyst-facing outputs deterministik hale gelmeden,
- error and failure propagation standardize edilmeden,
- ACTIVE_MATCH execution evidence tekrar üretilebilir hale gelmeden.

---

## 3. Product Boundary

HPFA çekirdeği hiçbir web framework'üne, mobil framework'e veya vendor-specific API'ye bağımlı olmayacaktır.

Core engine şu özellikleri taşımalıdır:

- CLI'dan çalışabilir,
- dosya tabanlı çalışabilir,
- internet bağlantısı olmadan çalışabilir,
- deterministic input/output üretir,
- JSON/TXT çıktılarıyla doğrulanabilir,
- aynı input için aynı contract altında aynı sonucu verir,
- frontend olmadan test edilebilir,
- API olmadan release edilebilir.

Web veya aplikasyon katmanı yalnızca şu rolleri üstlenebilir:

```text
input selection
run invocation
status display
evidence visualization
analyst navigation
report viewing
```

Şu rolleri üstlenemez:

```text
metric truth
claim decision
canonicalization
formula execution
business logic
runtime authority
```

---

## 4. Future Platform Shape

Uzun vadeli mimari:

```text
[HPFA CORE ENGINE]
  canonical ingest
  quality gates
  identity binding
  time/space normalization
  action identity
  phase/possession/sequence candidates
  metric primitives
  composite evidence
  claim routing
  football output audit
  report assembly

        ↓ stable contracts

[HPFA SERVICE LAYER]
  job submission
  run status
  artifact registry
  report retrieval
  version exposure
  auth boundary

        ↓

[CLIENTS]
  web
  mobile
  desktop
  analyst console
```

Core engine, service layer veya client olmadan da ürün olarak çalışabilmelidir.

Service layer, core engine'in iç mantığını yeniden yazmamalıdır.

Clients, engine outputlarını yorumlayamaz veya değiştiremez; yalnızca sunar.

---

## 5. Required Core Contracts Before UI

UI çalışmalarından önce aşağıdaki contract'lar ürünleşmelidir:

1. `SourceSurfaceContract`
2. `CanonicalActionCandidateContract`
3. `MetricPrimitiveContract`
4. `ContextSliceContract`
5. `EvidencePacketContract`
6. `ClaimEligibilityContract`
7. `RuntimeStatusContract`
8. `AnalystReportContract`
9. `FailureEnvelopeContract`
10. `ArtifactManifestContract`

Her contract:

- versioned,
- machine-readable,
- test-covered,
- backward-compatibility policy sahibi,
- claim boundary içerir durumda olmalıdır.

---

## 6. API Readiness Without Premature API Work

Bugün API geliştirilmez.

Fakat core outputları gelecekte API'ye bağlanabilecek kadar temiz olmalıdır.

Bunun için her executable module:

- stdin bağımlılığı olmadan çalışmalı,
- explicit input path almalı,
- explicit output path almalı,
- structured JSON output üretmeli,
- exit code kullanmalı,
- error status standardına uymalı,
- stdout'u insan anlatısı için değil machine summary için kullanmalı,
- side effect'leri sınırlandırmalıdır.

Bu yaklaşım API yazmadan API-readiness sağlar.

---

## 7. Non-Negotiable Core Qualities

Web veya aplikasyon öncesi motor şu kalite kapılarından geçmelidir:

### Correctness
- formula tests
- edge-case tests
- deterministic outputs
- lineage preservation

### Explainability
- support rows
- source lineage
- formula version
- claim ceiling
- counter-evidence

### Portability
- Termux
- Linux
- local filesystem
- no mandatory cloud dependency

### Maintainability
- modular contracts
- low coupling
- no circular dependency
- stable naming
- migration policy

### Release Safety
- PASS != RELEASE
- runtime evidence required
- ACTIVE_MATCH validation required
- production release separately declared

---

## 8. What Must Not Be Built Yet

Aşağıdaki işler çekirdek stabil olmadan ertelenmelidir:

- web dashboard
- mobile application
- live match UI
- user accounts
- subscription flows
- cloud job queue
- realtime websocket layer
- visual tactic boards
- public REST API
- multi-tenant storage

Bunlar yanlış değildir.

Ancak şu anda ürün sırasını bozarlar.

---

## 9. Current Product Order

Bugünkü öncelik:

```text
P0 runtime truth and source authority
P1 canonical ingest and action identity
P2 data quality and eligibility gates
P3 metric primitives
P4 context, phase, possession and sequence candidates
P5 evidence fusion and claim routing
P6 analyst report and football output audit
P7 stable artifact contracts
P8 service boundary
P9 API
P10 web and mobile clients
```

P8-P10, P0-P7 ACTIVE_MATCH üzerinde kanıtlanmadan açılmamalıdır.

---

## 10. Decision Test For Every New Proposal

Her yeni fikir şu sorularla değerlendirilmelidir:

1. Core engine doğruluğunu artırıyor mu?
2. Contract kalitesini artırıyor mu?
3. ACTIVE_MATCH üzerinde kanıt üretir mi?
4. Analyst evidence üretir mi?
5. Claim safety artırıyor mu?
6. Gelecekte API veya client tarafından yeniden kullanılabilir mi?
7. UI bağımlılığı yaratıyor mu?
8. Bugünkü runtime blocker'ı çözüyor mu?

Bir fikir yalnızca gelecekteki arayüz için değerliyse ama core engine'e katkı sağlamıyorsa ertelenir.

---

## 11. Release Gate For Service And Clients

Service layer çalışmaları ancak şu koşullarda başlayabilir:

```text
canonical contracts stable
core module outputs versioned
failure envelope stable
runtime ledger repeatable
analyst report deterministic
claim routing tested
ACTIVE_MATCH evidence pass
```

Web veya mobil client çalışmaları ancak service boundary stabilize olduktan sonra başlayabilir.

---

## 12. Final Directive

HPFA önce kusursuz bir motor olmalıdır.

Web sitesi ve aplikasyon bu motorun alternatifi değildir.

Onlar yalnızca sağlam motorun erişim katmanlarıdır.

Bugünkü ürün davranışı:

```text
Do not optimize for presentation.
Optimize for truth, evidence, contracts, repeatability and analyst value.
```

Son karar:

```text
ENGINE_FIRST
PLATFORM_READY_LATER
```

---

## Release Status

```text
SPEC_ONLY
```

Bu belge executable module değildir.
Ürün sırasını ve gelecekteki platform sınırlarını tanımlar.
