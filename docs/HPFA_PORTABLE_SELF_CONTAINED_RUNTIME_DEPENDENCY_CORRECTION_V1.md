# HPFA Portable Self Contained Runtime Dependency Correction V1

NODE: hpfa_portable_self_contained_runtime_dependency_correction_v1
STATUS: POLICY_CORRECTION_PASS

## Decision

HPFA must not depend on Google Drive or Dropbox at runtime.

Google Drive and Dropbox can support research, donor review, archive retrieval and governance history. They cannot be required for product execution.

## Football Product Translation

Drive and Dropbox are the club library and archive. The team may study them during preparation.

But on match day, the analysis system must work without opening the library.

## Correct Product Rule

A released HPFA module must be self-contained inside the canonical product tree.

Required runtime material must live in the portable package, not in Drive or Dropbox.

## Correct Authority Roles

Termux ACTIVE_MATCH: execution proof during validation.
GitHub canonical tree: source shelf for validated portable product code.
Google Drive: governance plus donor library, not runtime dependency.
Dropbox: research plus donor archive, not runtime dependency.
PDF and documents: reference only, not event truth.

## Correction To Previous Language

Drive and Dropbox are donor libraries, but donor library does not mean runtime dependency.

Donor knowledge must be extracted, adapted, reduced and embedded into HPFA contracts, policies, tests or documentation inside the product tree.

## Product Packaging Requirement

Future module packages must include:

- code
- contracts
- policies
- templates
- tests
- claim boundaries
- offline reference summaries
- sample-free runtime instructions

They must not require live Drive or Dropbox reads.

## Immediate Impact

The next node changes from donor library deep index as an end in itself to portable donor distillation.

## Next Node

hpfa_donor_library_to_portable_core_distillation_v1

## Decision

POLICY_CORRECTION_PASS
