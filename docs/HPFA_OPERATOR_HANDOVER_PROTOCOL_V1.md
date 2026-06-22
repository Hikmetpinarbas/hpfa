# HPFA Operator Handover Protocol V1

## Purpose

When the HPFA operator changes, the work must continue as if no handover occurred.

A new operator must understand from one file:

- what was done
- where the work stopped
- what evidence was produced
- what decisions were made
- which risks remain open
- what the next command status is

## Mandatory Handover Files

At the end of every critical node, produce one of:

```text
handover/current_operator_handover.md
```

or, in the output folder:

```text
hpfa_operator_handover_current.md
```

## Required Format

Every handover must include exactly these sections:

1. PROJECT
2. ACTIVE FRONTIER
3. CURRENT NODE
4. NODE STATUS
5. WHAT WAS DONE
6. EVIDENCE PRODUCED
7. DECISION
8. WHY THIS DECISION
9. FOOTBALL VALUE LEVEL
10. FOOTBALL VALUE NOTE
11. PORTABILITY STATUS
12. CLAIM SAFETY STATUS
13. OPEN RISKS
14. BLOCKERS
15. NEXT NODE
16. NEXT NODE PURPOSE
17. NEXT COMMAND STATUS
18. DO NOT REPEAT
19. REQUIRED CONTEXT FOR NEXT OPERATOR
20. HANDOVER SUMMARY

## Node Status Enum

```text
PASS
FAIL
FAIL_CLOSED
PASS_EMPTY
REVIEW_REQUIRED
BLOCKED
```

## Football Value Level Enum

```text
NO_FOOTBALL_GAIN
THEORETICAL_GAIN
EXPECTED_GAIN
VERIFIED_GAIN
```

## Portability Status Enum

```text
PORTABLE
DEV_PATH_ONLY
ABSOLUTE_PATH_RISK
UNKNOWN
```

## Claim Safety Status Enum

```text
CLAIM_GATE_CLOSED
CLAIM_SAFE
CLAIM_RISK_FOUND
NOT_APPLICABLE
```

## Next Command Status Enum

```text
READY
NEEDS_COORDINATOR
NEEDS_USER_FILE
BLOCKED
```

## Evidence Rule

Evidence produced must include:

```text
path
line count
byte size
sha256
short meaning
```

## New Operator First Response Format

A new operator must start with:

```text
READ_HANDOVER=YES
CURRENT_FRONTIER=...
CURRENT_NODE=...
LAST_STATUS=...
NEXT_NODE=...
READY_TO_CONTINUE=YES/NO
```

## Permanent Prohibitions

- Do not open a new architecture.
- Do not re-litigate settled decisions.
- Do not change state without evidence.
- Do not rerun the previous node unless instructed.
- Do not confuse PASS with execution.
- Do not confuse READY with EXECUTED.
- Do not create authority outside ACTIVE_MATCH.

## Handover Principle

One operator leaves, another enters.

HPFA memory must not break.

Every node leaves its evidence, decision, and next task.
