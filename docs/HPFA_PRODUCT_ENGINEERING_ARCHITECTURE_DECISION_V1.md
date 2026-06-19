# HPFA Product Engineering Architecture Decision V1

Project: HPFA Productization Program

Decision status: APPROVED BY COORDINATOR

## 1. Product Engineering Phase

HPFA research phase is closed as the default mode.

The active phase is Product Engineering.

Controlled research remains available only as a supporting exception.

## 2. Standard Product Module Pipeline

MODEL_B is approved with revision.

Every Product Module must use the same standard pipeline. New workflows are not designed per module.

Standard pipeline:

1. Module Scoped Discovery
2. Composite Scope
3. Candidate Pool
4. Composite Selection
5. ACTIVE_MATCH Validation
6. Football Output Audit
7. Release Decision
8. Coordinator Approval
9. Registry Write
10. Production Binding

## 3. Module Scoped Discovery

Global discovery is retired for normal sprint operation.

At sprint start, discovery is limited to the current Product Module and its related capability families.

## 4. Composite Apparatus Lifecycle

Composite Apparatus is now an official lifecycle layer between Capability Family and Product Module.

Official hierarchy:

Capability Family
-> Composite Apparatus
-> Product Module
-> Product Release
-> Commercial Module

Each Composite Apparatus must be independently versioned, tested, reused, improved and bound to one or more Product Modules where appropriate.

## 5. Product Lifecycle

Official lifecycle states:

DISCOVERED
CONSOLIDATED
COMPOSITE_READY
EXECUTION_READY
ACTIVE_MATCH_VALIDATED
FOOTBALL_VALIDATED
RELEASE_CANDIDATE
COORDINATOR_APPROVED
REGISTRY_WRITTEN
PRODUCTION_BOUND
COMMERCIAL_MODULE
MAINTAINED
EVOLVED

## 6. Registry Policy

Registry Write is allowed only after Coordinator Release Approval.

Release Candidate, Registry Write and Production Binding are separate maturity states.

## 7. Sprint Policy

Sprint is a time-management tool, not the primary architecture object.

Primary management object is Product Module, with Composite Apparatus as the reusable internal product unit.

## 8. Current Status

PROGRESSION_ENGINE reached Release Candidate status for POSTMATCH_RELEASE_0.1.

It is not registry-written and not production-bound.

Before Sprint 2, PROGRESSION_ENGINE must complete:

1. Composite Review
2. ACTIVE_MATCH Regression Test
3. Portable Runtime Test

## 9. Success Metrics

HPFA success is not measured by file count, node count or idea count.

Success metrics are:

1. Number of reusable Composite Apparatus units.
2. Number of Product Modules passing ACTIVE_MATCH validation.
3. Number of Product Modules reaching Commercial Module maturity.
