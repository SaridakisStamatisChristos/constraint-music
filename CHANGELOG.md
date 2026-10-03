# Changelog

## 2.1.0a1 — rhythm and motif grammar

- Promoted melody rhythm to an explicit CP-SAT dimension with `onset`, `tie`, and `rest` states.
- Added verified per-bar onset/rest/tie density, downbeat articulation, maximum rest runs, and maximum tie runs.
- Made ties preserve pitch and render as sustained MIDI notes; rests now create real silence in the melody track.
- Added motif grammar with exact repetition and exact semitone transposition between configured phrase locations.
- Extended the independent contract from 16 to 21 hard rules (`CM001`–`CM021`).
- Added v2.1 JSON provenance; semantic hashes now commit to rhythm as well as pitch/harmony/tension.
- Added rhythm/motif adversarial tests, MIDI duration tests, documentation, and an expressive example spec.
- Preserved v2.0 generation behavior by keeping rhythm generation opt-in.

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
