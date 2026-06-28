# HPFA Football Intelligence Research Log Template

Kayıt tipi: AR-GE / araştırma günlüğü  
Amaç: HPFA'nın futbolun matematiksel işletim sistemi için hipotez, mekanizma, formül, disiplin ve red-team hafızasını tutmak.  
Runtime authority: Bu dosya runtime truth değildir. ACTIVE_MATCH dışı bütün kayıtlar reference-only kabul edilir.

---

## Research Log Entry — RLOG-00X

### 1. Araştırma Başlığı

- Başlık:
- Tarih:
- İlgili product node:
- İlgili apparatus:
- Kaynak türü:
  - `GITHUB_PRODUCT_REPO`
  - `GITHUB_DONOR_REPO`
  - `DRIVE_GOVERNANCE`
  - `DRIVE_DONOR_LIBRARY`
  - `DROPBOX_ARCHIVE`
  - `DROPBOX_DONOR_LIBRARY`
  - `SIDER_ACADEMIC_BACKING`
  - `TERMUX_RUNTIME_EVIDENCE`
  - `ACTIVE_MATCH_RUNTIME_AUTHORITY`

---

### 2. Yeni Hipotezler

Her hipotez şu formatta yazılır:

```text
HYP-ID:
Hipotez:
Event-only dayanak:
Gerekli minimum veri:
Yanlışlayacak veri:
Claim seviyesi:
Durum: IDEA / RESEARCH / SPEC / PROTOTYPE / ACTIVE_MATCH / REJECTED / VALIDATED
```

---

### 3. Yeni Mekanizmalar

- Mekanizma adı:
- Hangi futbol davranışını açıklıyor?
- Input evidence:
- Output reading:
- Alternatif açıklamalar:
- Red-team notu:

---

### 4. Yeni Formüller / Ölçüm Adayları

```text
FORMULA-ID:
Ad:
Amaç:
Girdi:
Formül / hesap mantığı:
Ne ölçer:
Ne ölçmez:
Mevcut metriklerden farkı:
Karar kalitesini artırıyor mu:
Claim boundary:
Bakım maliyeti:
Status:
```

---

### 5. Kullanılabilecek Bilimsel Disiplinler

Her disiplin yalnızca açıklayıcı katkı sağlıyorsa yazılır. Analoji kanıt değildir.

| Disiplin | Kullanım amacı | Event-only uyumluluk | Risk | Status |
|---|---|---|---|---|
| Matematik |  |  |  |  |
| İstatistik |  |  |  |  |
| Fizik |  |  |  |  |
| Biyoloji |  |  |  |  |
| Ağ bilimi |  |  |  |  |
| Bilgi teorisi |  |  |  |  |
| Oyun teorisi |  |  |  |  |
| Psikoloji |  |  |  |  |

---

### 6. Event-Only Workaround'lar

Tracking/video gerektiren konular için yalnızca proxy/hipotez üretilebilir.

```text
WORKAROUND-ID:
Asıl kavram:
Neden doğrudan ölçülemez:
Event-only proxy:
Kanıt seviyesi:
Yanlışlama koşulu:
Kullanılabilecek güvenli dil:
Yasak dil:
Status:
```

---

### 7. Red-Team Notları

- Gizli varsayım:
- Doğrulama yanlılığı riski:
- Seçim yanlılığı riski:
- Örneklem hatası riski:
- Bağlam eksikliği:
- Alternatif açıklama:
- Bu fikri neden reddetmeliyiz?

---

### 8. İptal Edilen Fikirler

| Fikir | Neden iptal edildi | Tekrar açılma koşulu |
|---|---|---|
|  |  |  |

---

### 9. Kanıtlanan / Güçlenen Fikirler

| Fikir | Kanıt türü | ACTIVE_MATCH var mı? | Status |
|---|---|---|---|
|  |  |  |  |

---

### 10. Product Engineering'e Aktarım

- Aktarılacak mı? `YES/NO/WAIT`
- Hedef modül:
- Hedef apparatus:
- Gerekli contract:
- Gerekli test:
- Gerekli ACTIVE_MATCH validation:
- Analyst-facing output:

---

## Research Discipline Rules

1. Araştırma doğrudan product code değildir.
2. Donor veya akademik kaynak runtime truth değildir.
3. Her hipotez yanlışlanabilir olmalıdır.
4. Her formül bakım maliyetini haklı çıkarmalıdır.
5. Her football reading event-only claim boundary içinde kalmalıdır.
6. Yeni terminoloji yeni bilgi üretmiyorsa reddedilir.
