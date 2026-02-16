# Possession State Machine – Canonical v1.0.0

## Purpose
Bu doküman, HPFA analiz motorunda mülkiyet (possession) akışının
deterministik ve fail-closed şekilde nasıl çözüleceğini tanımlar.
Bu doküman **tek kaynak gerçektir** (Single Source of Truth).

---

## States
- CONTROLLED   : Net ve doğrulanmış mülkiyet
- CONTESTED    : Mücadele / belirsizlik anı
- DEAD_BALL    : Oyun durmuş durumda

---

## Canonical Events
- PASS (success / fail)
- DRIBBLE (success / fail)
- TACKLE
- INTERCEPTION
- LOOSE_BALL
- RESTART_KICKOFF
- RESTART_THROWIN
- RESTART_CORNER
- RESTART_FREEKICK
- OUT
- FOUL

---

## Transition Rules

| From State | Event              | To State    | Possession Effect |
|-----------|--------------------|------------|-------------------|
| DEAD_BALL | RESTART_*          | CONTROLLED | START             |
| CONTROLLED| PASS (success)     | CONTROLLED | CONTINUE          |
| CONTROLLED| DRIBBLE (success)  | CONTROLLED | CONTINUE          |
| CONTROLLED| TACKLE             | CONTESTED  | NEUTRAL           |
| CONTROLLED| INTERCEPTION       | CONTROLLED | START             |
| CONTESTED | INTERCEPTION       | CONTROLLED | START             |
| CONTESTED | TACKLE             | CONTESTED  | NEUTRAL           |
| ANY       | OUT / FOUL         | DEAD_BALL  | END               |
| ANY       | LOOSE_BALL         | CONTESTED  | NEUTRAL           |

---

## Invariants (Fail-Closed)

- DEAD_BALL state’inde possession_id **NULL** olmalıdır
- START yalnızca CONTROLLED state ile başlar
- Aynı timestamp + aynı team_id → atomic event (birleştirilir)
- Tanımsız event → UNVALIDATED
- Tanımsız transition → ERROR

---

## Scramble Buffer Rule

- 0.5 saniyeden kısa süreli sahipsiz anlar
  possession değişimi yaratmaz
- Bu süre içerisinde gelen temaslar
  aynı possession altında tutulur

---

## Undefined Behaviour

- Bu dokümanda tanımlı olmayan hiçbir
  event veya geçiş kabul edilmez
- Sistem bu durumda **fail-closed** çalışır
