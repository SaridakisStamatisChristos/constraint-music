# Changelog

## 2.3.0a1 — distinct enumeration and Pareto search

- Replaced seed-only `generate_many()` variation with CP-SAT no-good cuts that guarantee distinctness over selected musical dimensions.
- Added explicit distinctness dimensions for melody, rhythm, bass, and harmony.
- Split the scalar objective into five named minimized components: tension deviation, melody motion, bass motion, harmonic repetition, and contour mismatch.
- Added independent objective-vector recomputation from serialized musical values; solver-side and independent vectors must agree.
- Added deterministic weighted scalarization profiles and a bounded Pareto-front approximation API.
- Added independent Pareto dominance filtering and deterministic single-worker enumeration tests.
- Versioned JSON artifacts to schema 2.3 with integrity-protected objective-vector metadata.
- Added CLI controls for distinct dimensions, Pareto mode, and Pareto candidate-pool size.
- Kept the hard musical certification contract unchanged at `CM001`–`CM026`; v2.3 changes search/ranking semantics, not feasibility semantics.

## 2.2.0a1 — verified phrase grammar

- Added explicit phrase spans with unique IDs and non-overlap/in-bounds validation.
- Added phrase roles: `statement`, `antecedent`, `consequent`, `transition`, and `cadential`.
- Added exact phrase relations: `independent`, `repeat`, `transpose`, `answer`, and `sequence`.
- Added precise phrase-local cadence labels: `tonic_close`, `dominant_open`, `dominant_to_tonic`, and `leading_tone_to_tonic`.
- Added a minimal answer-linked antecedent/consequent period grammar with open-to-strong closure semantics.
- Extended the hard contract from 21 to 26 rules (`CM001`–`CM026`) with independent phrase verification.
- Versioned JSON provenance to schema/contract 2.2; phrase declarations are committed by the semantic digest through the serialized specification.
- Added Phase 0 stabilization regressions for old all-onset configs, malformed rhythm deserialization, deterministic single-worker generation, and tamper detection.
- Added positive and adversarial phrase tests plus an eight-bar period example.
- Kept the historical `require_authentic_cadence` field backward compatible while documenting it as the legacy whole-piece closure rule.

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
