# Changelog

## 2.6.0a1 — verified applied-dominant tonicization

- Added opt-in applied-dominant tonicization on top of the v2.5 `triads+sevenths` vocabulary.
- Added explicit nullable per-beat tonicization-target metadata, kept orthogonal to global chord degree, chord kind, inversion, and SATB voicing.
- Added target-derived dominant-seventh construction instead of unrestricted chromatic pitch permission or opaque slash-chord labels.
- Added structural filtering of tonicization targets that cannot preserve the established CM005/CM006 outer-voice semantics.
- Added complete applied-dominant SATB realization with root, first, and second inversions under the preserved outer-voice contract.
- Added solver-native immediate resolution to the declared local tonic, downward applied chordal-seventh resolution, and upward local-leading-tone resolution in every SATB voice.
- Extended the independent hard contract from 36 to 40 rules (`CM001`–`CM040`) with separate tonicization-context, realization, target-resolution, and tendency-resolution IDs.
- Added independent reconstruction of applied-dominant pitch content and resolution from ordinary serialized musical values.
- Added `tonicization` as a separate no-good distinctness dimension without redefining `harmony`, `harmonic_form`, or `voicing`.
- Versioned JSON artifacts and the hard-rule contract to 2.6; semantic provenance now commits tonicization target metadata when present.
- Preserved loading and musical verification of older SATB/harmonic-form payloads without inventing tonicization metadata when the feature is disabled.
- Added positive forced `I -> V7/V -> V -> I -> V -> I` generation coverage and adversarial tests for forged targets, wrong target resolution, unresolved local tendency tones, and provenance tampering.
- Kept modal mixture, secondary leading-tone chords, persistent local-key regions, modulation, and third-inversion sevenths outside the v2.6 boundary.

## 2.5.0a1 — expanded harmonic vocabulary

- Added an opt-in `triads+sevenths` harmonic vocabulary while preserving `triads` as the default for backward-compatible specifications.
- Added structured `ChordKind` identity and explicit per-beat inversion metadata.
- Added complete diatonic seventh-chord realization inside the SATB CP-SAT model.
- Added root, first, and second inversion support while preserving the established CM005/CM006 triadic-core semantics for outer voices.
- Added solver-native downward chordal-seventh resolution and explicit dominant-seventh-to-tonic behavior with leading-tone resolution in every SATB voice.
- Extended the independent hard contract from 32 to 36 rules (`CM001`–`CM036`).
- Added the `harmonic_form` distinctness dimension for chord kind/inversion while preserving `harmony` as chord-degree-sequence distinctness.
- Versioned JSON artifacts to schema 2.5; semantic provenance now commits harmonic kind/inversion metadata when present.
- Preserved loading and musical verification of older SATB artifacts without inventing missing harmonic-form metadata.
- Added positive solver tests plus adversarial tests for inversion mismatch, unresolved sevenths, wrong dominant targets, and harmonic-form provenance tampering.
- Kept chromatic applied dominants, modal mixture, tonicization/local-key contexts, and modulation outside the v2.5 boundary.

## 2.4.0a1 — solver-native SATB harmony

- Added explicit beat-level soprano, alto, tenor, and bass SATB realization inside CP-SAT.
- Anchored soprano to the strong-grid melody while solving alto and tenor independently.
- Added canonical inner-voice ranges, strict voice ordering, and octave upper-voice spacing.
- Added complete-triad enforcement with an explicit root-doubling policy.
- Added solver-native parallel-perfect avoidance for every voice pair involving alto or tenor.
- Added solver-native leading-tone resolution for alto and tenor.
- Extended the independently verified hard contract from 26 to 32 rules (`CM001`–`CM032`).
- Added `SatbGenerationResult` serialization and artifact schema 2.4; semantic digests now commit to SATB voices.
- Preserved v2.3 `harmony` distinctness as chord-sequence distinctness and added a separate `voicing` dimension for alto/tenor realizations.
- Added positive SATB generation tests and adversarial verification tests for crossing and chord-completeness tampering.
- Cached immutable SATB chord and parallel-motion tables to avoid rebuilding the same transition relations across repeated solves.

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
