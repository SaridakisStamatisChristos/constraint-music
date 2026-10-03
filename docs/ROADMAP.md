# Roadmap

## v2 foundation

- [x] Recover v1.1 CP-SAT generator behavior.
- [x] Version the hard-constraint contract.
- [x] Complete independent verification of solver hard rules.
- [x] Fail closed on solver/verifier disagreement.
- [x] Add verifiable JSON provenance.
- [x] Add offline `verify` command.

## v2.1 expressive structure

- [x] Rhythm CSP: explicit onsets, ties, rests, density, run limits, metrical downbeats.
- [x] Motif grammar: exact repetition and exact semitone transposition with rhythm inheritance.

## v2.2 phrase grammar

- [x] Explicit non-overlapping phrase spans and stable phrase IDs.
- [x] Phrase roles and precise phrase-local cadence semantics.
- [x] Phrase relations: independent, repeat, transpose, answer, sequence.
- [x] Minimal answer-linked antecedent/consequent period grammar.
- [x] Independent phrase verification and adversarial tamper tests.

## v2.3 distinct enumeration and Pareto search

- [x] CP-SAT no-good cuts for genuinely distinct alternatives.
- [x] Explicit distinctness dimensions: melody, rhythm, bass, and harmony.
- [x] Named objective-vector metadata with independent recomputation.
- [x] Deterministic scalarization profiles and Pareto-front approximation.

## v2.4 solver-native multi-voice harmony

- [x] Explicit soprano/alto/tenor/bass solver variables.
- [x] Voice ranges, ordering, spacing, chord completeness, and doubling policy.
- [x] Inner-voice parallel-perfect and tendency-tone resolution rules.
- [x] Independent SATB verification and artifact-provenance coverage.
- [x] Separate SATB `voicing` no-good dimension while preserving `harmony` semantics.

## v2.5 expanded harmonic vocabulary

- [x] Preserve triads as the default and make seventh-chord vocabulary opt-in.
- [x] Structured chord kind and explicit inversion representation.
- [x] Complete diatonic seventh chords in solver-native SATB.
- [x] Root, first, and second inversions under the preserved outer-voice contract.
- [x] Chordal-seventh downward-step resolution.
- [x] Dominant-seventh-to-tonic and leading-tone resolution.
- [x] Independent CM033–CM036 verifier symmetry and adversarial tests.
- [x] `harmonic_form` distinctness without redefining legacy `harmony`.
- [x] Schema 2.5 provenance for harmonic kind/inversion metadata.

## v2.6 verified tonicization

- [x] Explicit nullable local tonicization-target identity.
- [x] Target-derived applied dominant seventh construction.
- [x] Structural filtering of targets incompatible with preserved CM005/CM006 semantics.
- [x] Complete SATB realization of root/first/second-inversion applied dominants.
- [x] Immediate resolution to the declared local tonic.
- [x] Applied chordal-seventh and local-leading-tone resolution.
- [x] Independent CM037–CM040 verifier symmetry and adversarial tamper tests.
- [x] `tonicization` distinctness without redefining `harmony` or `harmonic_form`.
- [x] Schema/contract 2.6 provenance for tonicization target metadata.

## Later harmonic expansion

- [ ] Modal mixture / borrowed-chord representation with explicit source-mode identity.
- [ ] Secondary leading-tone chords with independent tendency-tone semantics.
- [ ] Persistent local-key regions distinct from one-chord tonicization.
- [ ] Controlled modulation with explicit pivot and destination-key identity.
- [ ] Third-inversion seventh support if the outer-voice compatibility contract is explicitly revised rather than silently reinterpreted.

## Later general work

- [ ] Richer rhythmic syntax and motif transformations.
- [ ] Binary/ternary/period/form grammar.
- [ ] Transparent style profiles.
- [ ] Unsat explanations mapped back to musical rules and configuration fields.
- [ ] MusicXML export and notation-level regression fixtures.

## Neuro-symbolic track

A model may propose motifs, harmonic plans, rhythmic cells, phrase plans, tonicization targets, or target curves, but only the symbolic layer is allowed to certify the final artifact. The intended boundary is `proposal -> compile/repair -> independent verify -> export`, not unconstrained model generation presented as verified composition.
