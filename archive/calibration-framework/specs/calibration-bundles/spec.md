# Delta for Calibration Bundles

**Extends**: `paper-trading` (REQ-PT-005: Evidence Bundling)
**RFC**: RFC-004 §Paper Trading Operational Contract

---

## ADDED Requirements

### Requirement: Calibration Evidence Bundles

The system SHALL produce calibration evidence bundles as filesystem artifacts distinct
from session bundles. Directory: `paper_trading/cal-NNN/` where `cal-NNN` is a
UTC calendar day. Format: SHA-256 checksum manifest.

#### Scenario: Calibration bundle written to separate directory

- GIVEN evidence report generated on 2026-07-20
- WHEN bundle is created
- THEN written to `paper_trading/cal-020/`, NOT `paper_trading/dia-020/`

### Requirement: Bundle Contents

Each calibration bundle SHALL contain:
- `evidence_report-HHMMSS.json` — full EvidenceReport (AIC, BIC, χ², entropy, persistence)
- `adopted_config-HHMMSS.json` — {states, generator, evidence_ref, adopted_at, operator}
- `provenance-HHMMSS.json` — manifest with SHA-256 of both files, timestamp, hostname
- `manifest-HHMMSS.json` — bundle-level integrity checksum

`HHMMSS` timestamp suffix SHALL prevent overwrites from concurrent calibration runs.

#### Scenario: All four files present

- GIVEN `calibrate adopt` completed successfully
- WHEN bundle is written
- THEN directory contains evidence_report, adopted_config, provenance, and manifest
- AND manifest JSON includes SHA-256 of the other three files

### Requirement: Regenerability

Bundles SHALL be regenerable from DB state: replaying the same DB at the same state SHALL
produce byte-identical bundle files. This REQUIRES deterministic JSON serialization
(`sort_keys=True`, fixed precision floats).

#### Scenario: Regenerated bundle matches original

- GIVEN DB snapshot at adoption point and original bundle
- WHEN bundle regenerated from DB
- THEN SHA-256 of regenerated files matches original manifest checksums

### Requirement: Separation from Session Bundles

Calibration bundles SHALL use the naming prefix `cal-NNN` and session bundles SHALL
continue using `dia-NNN`. No shared directory. A manifest validation that finds
calibration artifacts in `dia-NNN/` or session artifacts in `cal-NNN/` SHALL raise
a warning.

#### Scenario: Cross-contamination detected

- GIVEN evidence_report.json accidentally in `dia-020/`
- WHEN manifest validation runs
- THEN warning raised: "Calibration artifact in session bundle directory"
