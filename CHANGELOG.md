# Changelog

## 2.0.0a1 — revival baseline

- Rebuilt the recovered v1.1 constraint-programming engine as a clean v2 foundation.
- Added a versioned 16-rule hard-constraint contract with stable rule IDs.
- Closed the v1.1 verifier gaps for melodic tritones, bass tritones, and large-leap recovery.
- Added fail-closed solver/verifier contract enforcement.
- Added independently re-verifiable JSON artifacts with SHA-256 composition and contract digests.
- Added `constraint-music verify` for offline validation without rerunning CP-SAT.
- Preserved deterministic seeded generation, MIDI export, custom progression graphs, tension curves, and harmonic-minor support.
- Added adversarial verifier tests and CI quality gates.

## 1.1.0 — recovered historical implementation

- CP-SAT melody/bass/harmony generation.
- Configurable functional progression graph.
- Subdivision-level parallel-perfect prevention.
- MIDI and JSON output.
