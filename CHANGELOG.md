# Changelog

## 2.7.0a1 — verified modal mixture

- Added opt-in modal mixture through explicit per-beat parallel-source identity.
- Added canonical source modes: parallel natural minor for global-major pieces and parallel major for global-minor pieces.
- Added source-derived borrowed triads without granting unrestricted chromatic pitch permission or storing harmony as opaque Roman-numeral strings.
- Preserved CM005/CM006 outer-voice semantics by carrying borrowed chromatic tones in inner voices and structurally filtering unsupported borrowed degrees.
- Preserved the global closure contract by prohibiting borrowing on the final beat and, under authentic cadence, on the penultimate beat.
- Made borrowing and tonicization mutually exclusive on a beat while allowing both features to coexist elsewhere in the same composition.
- Extended the independent hard contract from 40 to 42 rules with `CM041` modal-mixture context and `CM042` borrowed-chord realization.
- Added independent reconstruction of source-mode pitch classes, complete borrowed-triad realization, and inversion/bass agreement from serialized values.
- Added `modal_source` as a separate no-good distinctness dimension without redefining `harmony`, `harmonic_form`, `tonicization`, or `voicing`.
- Versioned package to `2.7.0a1` and artifact/contract schema to 2.7; semantic provenance now commits modal-source metadata.
- Preserved loading and musical verification of older payloads without inventing modal-source metadata when modal mixture is disabled.
- Added deterministic positive generation plus adversarial tests for forged source identity, degree/inversion tampering, provenance tampering, legacy loading, and modal-source distinctness.
- Kept borrowed sevenths, secondary leading-tone chords, persistent local-key regions, modulation, and third-inversion sevenths outside the v2.7 boundary.

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

- Added explicit beat-level soprano/alto/tenor/bass solver variables and independent SATB verification.
- Added voice ranges, ordering, spacing, complete-triad/root-doubling policy, inner-voice parallel-perfect avoidance, and inner leading-tone resolution.
- Extended the independently verified contract from 26 to 32 rules and added `voicing` distinctness.

## 2.3.0a1 — distinct enumeration and Pareto search

- Added CP-SAT no-good cuts, explicit distinctness dimensions, named objective vectors, independent objective recomputation, deterministic scalarizations, and bounded Pareto-front approximation.

## 2.2.0a1 — verified phrase grammar

- Added explicit phrase spans, roles, phrase relations, phrase-local cadence semantics, answer-linked antecedent/consequent structure, and independent phrase verification.

## 2.1.0a1 — rhythm and motif grammar

- Added explicit onset/tie/rest rhythm, bar-density/run constraints, real ties/rests in MIDI, and verified repeat/transpose motif grammar.

## 2.0.0a1 — revival baseline

- Rebuilt the recovered v1.1 CP-SAT engine with a versioned hard-rule contract, fail-closed independent verification, verifiable JSON provenance, and offline `verify`.

## 1.1.0 — recovered historical implementation

- CP-SAT melody/bass/harmony generation.
- Configurable functional progression graph.
- Subdivision-level parallel-perfect prevention.
- MIDI and JSON output.
