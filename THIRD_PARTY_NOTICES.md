# HPFA Third-Party and Redistribution Notice

Status: **REVIEW_REQUIRED before external/commercial distribution**.

HPFA's canonical football-intelligence core intentionally declares no mandatory
third-party Python runtime dependency in pyproject.toml. Optional capabilities
are isolated so a missing optional package only affects the capability that needs it.

## Declared optional dependencies

| Scope | Package | Role | License state |
|---|---|---|---|
| xls | xlrd | legacy .xls support | BSD family; verify bundled notice at release |
| reference | pypdf | reference-document support | BSD-3-Clause |
| dev | pytest | tests only | MIT |
| dev | openpyxl | XLSX test/bootstrap fixtures | MIT |
| legacy-tools | numpy, pandas, matplotlib, mplsoccer | non-core historical/visual tools | redistribution review required before shipping those tools |

legacy-tools is not part of the claim-safe runtime core and must not become a
hidden production dependency.

## Vendor / donor boundary

vendor/hp_engine and vendor/hp_cdl are research/provenance surfaces, not
approved product dependencies. The current snapshots do not contain a verified
license file at their vendor roots. They are therefore **EXCLUDE_FROM_DISTRIBUTION**
until provenance, copyright, commercial-use and redistribution rights are resolved.

External repositories named in HPFA research metadata are references, not bundled
runtime code unless separately admitted and licensed.

## Release rule

A release bundle must contain only:
1. HPFA-owned product code/assets;
2. third-party material with verified license and required notices;
3. user/provider match data only when redistribution rights explicitly permit it.

Unknown license, unknown data rights, or donor provenance => REVIEW_REQUIRED.
