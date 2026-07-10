# HPFA Donor-to-Product Operating Model V1

Kayıt tipi: Product governance / donor exploitation standard  
Çalışma dili: Türkçe  
Ana ilke: `ADAPT_NOT_COPY`  
Runtime authority: `runtime/active_single_match/current`  
Status: `SPEC_ONLY`  
Production release: `false`

---

## 1. Temel Karar

HPFA ana reposu donörlerden maksimum faydayı, donor kodunu içeri doldurarak değil, donor repolardaki güçlü fikirleri HPFA ürün sözleşmesine dönüştürerek sağlar.

Basit anlatım:

> Donörler oyuncu fabrikasıdır. `hpfa` A takım kadrosudur. Fabrikadaki herkesi A takıma alamazsın. İhtiyacın olan oyuncuyu seçer, geliştirir, teste sokar ve ancak hazırsa kadroya alırsın.

Ana risk donorların kullanılmaması değildir.

Ana risk:

> Çok sayıda iyi fikir bulunması fakat bunların tek ürün zincirine dönüşmemesi.

Donor bulgusu tek başına product capability değildir.

```text
donor idea
≠ HPFA capability
≠ runtime evidence
≠ production release
```

---

## 2. Donor Repo Rolleri

### HP-Motor — Behaviour / Runtime Primitive Donor

Ana değer:

- ingest
- provider mapping
- canonicalization
- source validation
- phase / possession / sequence primitives
- metric requirements
- no-input-no-module gates
- runtime health checks

HP-Motor'dan alınacak ana sorular:

- Hangi veri hangi modülü açar?
- Hangi veri eksikse hangi modül kapanır?
- Hangi dönüşüm canonical input adayı üretir?
- Hangi kayıp sessizce gerçekleşmemelidir?

En yüksek değerli donor ilkesi:

```text
NO_INPUT_NO_MODULE
```

HPFA-native dönüşüm:

```text
input capability
→ eligibility gate
→ required columns
→ available primitives
→ blocked modules
→ explicit reason
```

Bu ilke, veri yokken analiz uydurulmasını engeller.

---

### HP-Engine — Intelligence / Argument Donor

Ana değer:

- metric graph
- argument relations
- Popper / falsification logic
- registry gates
- contradiction structures
- orchestration concepts
- explanation routing

HP-Engine'den alınacak ana muhakeme hattı:

```text
Feature A
→ Feature B ile ilişkili mi?
→ bağlam bunu etkiliyor mu?
→ karşı kanıt var mı?
→ hipotez zayıflıyor mu?
→ geri çekilmeli mi?
```

Yüksek değerli donor fikirleri:

- metric dependency graph
- confound relationships
- mediates relationships
- feedback relationships
- contradiction links
- falsifiability gate

Kritik boundary:

Donörde yazan:

```text
A influences B
```

HPFA'da doğrudan gerçek kabul edilemez.

HPFA-native dönüşüm:

```text
declared_relation_candidate
support_requirement
context_requirement
counter_evidence_requirement
withdrawal_condition
claim_ceiling
```

Örnek:

```yaml
relation_candidate:
  source: field_tilt_surface
  target: final_third_entry_surface
  required_same_window: true
  minimum_support_surfaces: 2
  counter_scenarios:
    - possession_share_inflation
    - opponent_block_effect
  claim_output_allowed: false
```

Kural:

> Fikir alınır. İddia alınmaz.

---

### HP-PROJELERI — Governance / Authority Donor

Ana değer:

- governance
- canonical schema
- conflict maps
- gate policy
- verification
- source authority
- release language

Rol:

> Analitik motor değil; anayasa mahkemesidir.

Buradan alınacak sorular:

- Hangi kaynak neye yetkili?
- Hangi conflict nasıl çözülür?
- Hangi status ne anlama gelir?
- Hangi modül release'e hazırdır?
- Hangi output runtime truth sayılır?

HP-PROJELERI'nin görevi product code üretmek değildir.

Şunu garanti eder:

```text
donor idea
≠ product capability
≠ runtime evidence
≠ release
```

---

## 3. Donor Capability Registry

Donor kazısı insan hafızasına bağlı kalmamalıdır.

Her donor bulgusu makine-okunur kayda girmelidir.

Zorunlu alanlar:

```text
capability_id
source_repo
source_path
source_role
capability_family
problem_solved
target_hpfa_module
existing_in_main
adaptation_required
claim_risk
input_requirements
output_contract
required_tests
runtime_need
priority
decision
```

Örnek kayıt:

```yaml
capability_id: DONOR-ENGINE-POPPER-001
source_repo: HP-Engine
source_path: engine/popper_gate.py
source_role: GITHUB_DONOR_REPO
capability_family: contradiction_and_falsification
problem_solved: unsupported_argument_promotion
target_hpfa_module: defeasible_argument_router_lite
existing_in_main: partial
adaptation_required:
  - candidate_only_routing
  - explicit_counter_evidence
  - withdrawal_conditions
claim_risk: high
decision: ADAPT_LATER
```

Faydası:

- Aynı donor fikir tekrar tekrar kazılmaz.
- Kopya modül oluşmaz.
- Neyin eksik, alınmış veya reddedilmiş olduğu görünür.
- Ana repo donor çöplüğüne dönüşmez.

---

## 4. Donor Value Score

Her donor capability eşit değildir.

Önerilen değerlendirme:

```text
Donor Value Score =
Analyst Gain
× Reusability
× Evidence Compatibility
× Integration Readiness
÷ Claim Risk
÷ Maintenance Cost
```

Basit karar:

> Çok faydalı, kolay bağlanan ve güvenli fikir öne alınır. Havalı fakat veri istemeyen, yüksek iddia riski taşıyan veya zor bağlanan fikir bekler.

### Yüksek değer

- recursive forbidden-field scanner
- upstream failure propagation
- metric dependency registry
- counter-evidence router
- runtime ledger
- canonical field mapper

### Orta değer

- yeni metric formula
- yeni plot type
- yeni taxonomy family

### Düşük değer / şimdilik reddet

- coach intention detector
- dominance truth
- pitch control from events only
- fatigue inference without load/tracking
- off-ball structure from event rows

---

## 5. Donor-to-HPFA Zorunlu 10 Kapı

Bir capability `hpfa` içine ancak aşağıdaki kapılardan geçerse girebilir:

1. Source role
2. Exact donor path
3. Problem definition
4. Existing main overlap
5. HPFA-native contract
6. Claim boundary
7. Unit tests
8. Integration test
9. ACTIVE_MATCH need
10. Release status

Eksik kapı varsa:

```text
DO_NOT_MERGE
```

Büyüyen sistemlerde hızın sırrı daha çok şey eklemek değildir.

> Yanlış şeyin içeri girmesini zorlaştırmaktır.

---

## 6. Dört Adaptation Yöntemi

### A. Contract Adaptation

Donordaki fikrin giriş/çıkış sözleşmesini al.

Örnek:

```text
NO_INPUT_NO_MODULE
→ HPFA capability eligibility contract
```

### B. Algorithm Adaptation

Algoritmanın özünü al, HPFA inputlarına ve claim boundary'sine göre yeniden yaz.

Örnek:

```text
Popper gate
→ explicit counter-evidence router
```

### C. Registry Adaptation

Donordaki sabit bilgiyi registry'ye dönüştür.

Örnek:

```text
metric_graph.yaml
→ candidate relation registry
```

### D. Test Adaptation

Donordaki edge-case bilgisini regression testine dönüştür.

Örnek:

```text
silent data drop risk
→ test_no_silent_surface_drop
```

En düşük değerli yöntem:

```text
copy file
→ rename module
→ merge
```

Bu kısa vadede hızlı görünür; uzun vadede teknik borç üretir.

---

## 7. Gap Query First

Yanlış süreç:

```text
donor repoya bak
→ ilginç bir şey bul
→ ana repoya ekle
```

Doğru süreç:

```text
ana repodaki gap'i belirle
→ exact search query üret
→ donorları sırayla tara
→ en uygun capability'yi seç
→ HPFA-native üret
```

Örnek gap:

```text
Argument geri çekiliyor fakat graph'a nasıl taşınacağı belirsiz.
```

Search query:

```text
Which donor has withdrawal-state, falsifier, contradiction,
or argument-state propagation logic?
```

Search order:

```text
hpfa main
→ HP-Motor
→ HP-Engine
→ HP-PROJELERI
```

Bu yaklaşım donor odaklı geliştirmeyi ürün ihtiyacı odaklı geliştirmeye çevirir.

---

## 8. Donor-to-Product Compiler Standard

Buradaki compiler gerçek bir compiler olmak zorunda değildir.

Zorunlu dönüşüm hattıdır:

```text
Donor Capability
→ Capability Card
→ Gap Match
→ HPFA Contract
→ Implementation
→ Tests
→ Integration
→ Runtime Evidence
→ Release Decision
```

Her donor bulgusu yalnızca şu üç karardan birine gider:

```text
ADAPT_NOW
ADAPT_LATER
REJECT
```

`İlginç, bakarız` geçerli karar değildir.

---

## 9. Intelligence-Layer Arama Öncelikleri

Yüksek getirili donor arama aileleri:

- contradiction
- falsifier
- counter evidence
- withdrawal
- confounder
- dependency graph
- metric graph
- relation graph
- sequence motif
- change point
- uncertainty
- abstention
- failure propagation
- evidence provenance
- context binding
- argument state
- claim routing
- orchestration ledger

Düşük öncelik:

- bir tane daha pas metriği
- bir tane daha heatmap
- bir tane daha yüzdelik skor

Neden:

> 100 metrik sistemi 100 kat akıllı yapmaz.

Yüksek değerli intelligence mechanism:

```text
3 metriği bağla
→ bağlamını kontrol et
→ karşı kanıt ara
→ argümanı zayıflat
→ gerektiğinde geri çek
```

---

## 10. Integration Spine

Donorlardan gelen her yeni parça şu spine'a bağlanmalıdır:

```text
Source Authority
→ Canonical Surface
→ Eligibility Gate
→ Feature Primitive
→ Composite Evidence
→ Relation Fusion
→ Argument Candidate
→ Contradiction Search
→ Defeasible Route
→ Evidence Graph
→ Lens Completeness
→ Safe Language
→ Report Candidate
→ Runtime Ledger
```

Bağlanmayan modül ürün değildir.

Sadece kütüphane parçasıdır.

---

## 11. İki Zorunlu Kanıt

Her donor adaptation iki kanıt üretmelidir.

### Engineering Evidence

- Modül çalıştı mı?
- Hangi inputla çalıştı?
- Test geçti mi?
- Hangi output yazıldı?
- Hangi failure propagate edildi?

### Analyst Evidence

- Analiste ne kazandırdı?
- Hangi ilişkiyi görünür yaptı?
- Hangi yanlış yorumu engelledi?
- Hangi argümanı zayıflattı?
- Hangi eksik lensi gösterdi?

Sadece engineering evidence varsa:

```text
teknik olarak çalışıyor
ama product value kanıtlanmamış
```

Sadece analyst-facing dil varsa:

```text
analist-facing
ama güvenilirliği kanıtlanmamış
```

İkisi birlikte gerekir.

---

## 12. Current Priority Order

### P0 — Integration Safety

1. PR #139
2. Recursive forbidden-field guard
3. Defeasible Router → Evidence Graph contract
4. End-to-end Intelligence Chain test

Verified GitHub state at record time:

```text
PR #139
Title: Propagate packet failure into fusion
State: OPEN
Merged: false
Mergeable: true
Head: fix-fusion-upstream-packet-failure-v1
```

PR #139, upstream packet failure'ın Fusion katmanına güvenli olmayan biçimde sızmasını engellemeyi hedefleyen current integration-safety node olarak kaydedilir.

### P1 — Donor Exploitation Infrastructure

5. Donor Capability Registry
6. Donor Gap Query Template
7. Donor Value Scorer
8. Adaptation Decision Ledger

### P2 — Intelligence Gain

9. Contradiction Candidate Engine
10. Relation / Metric Graph Adapter
11. Knowledge Graph V2
12. Intelligence Pipeline Orchestrator

### P3 — Product Evidence

13. ACTIVE_MATCH execution
14. Engineering evidence ledger
15. Analyst evidence audit
16. Release decision

---

## 13. En Büyük Hata

Yanlış model:

```text
HP-Motor'dan ingest kodu al
HP-Engine'den graph kodu al
HP-PROJELERI'nden policy dosyası al
hepsini hpfa'ya at
```

Bu maksimum fayda değildir.

Bu maksimum teknik borçtur.

Doğru model:

```text
Donorlar:
fikir + algoritma + edge case + registry + test bilgisi

hpfa:
contract + integration + runtime + claim safety + product output
```

---

## 14. Tek Cümlelik Karar

> HPFA'nın donörlerden maksimum fayda sağlaması için daha fazla kod ithal etmesi değil, daha iyi bir donor-to-product dönüşüm sistemi kurması gerekir.

En yüksek kaldıraçlı yeni infrastructure node:

```text
HPFA Donor Capability Registry + Adaptation Ledger
```

Bu kurulursa her donor kazısı ürünü büyütür.

Kurulmazsa her donor kazısı repoyu şişirir.

---

## 15. Product Status

```text
SPEC_ONLY
```

Reason:

- Bu dosya donor-to-product çalışma standardını tanımlar.
- Executable registry veya scorer oluşturmaz.
- ACTIVE_MATCH evidence üretmez.
- PR #139 için merge/release kararı vermez.
- Sonraki doğru adım P0 integration safety hattını tamamlamak ve ardından registry/ledger contract'ını ayrı node olarak açmaktır.
