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
- [x] Phrase roles: statement, antecedent, consequent, transition, cadential.
- [x] Phrase relations: independent, repeat, transpose, answer, sequence.
- [x] Precise phrase cadence labels instead of broad cadence terminology.
- [x] Minimal answer-linked antecedent/consequent period grammar.
- [x] Independent phrase verification and adversarial tamper tests.
- [x] Eight-bar period example.

## v2.3 distinct enumeration and Pareto search

- [x] Replace seed variation as the primary alternative-generation mechanism with CP-SAT no-good cuts.
- [x] Allow explicit distinctness dimensions: melody, rhythm, bass, and harmony.
- [x] Add named objective-vector metadata with independent recomputation.
- [x] Add deterministic weighted scalarization profiles and Pareto-front approximation.
- [x] Test deterministic enumeration, metadata integrity, and Pareto dominance independently.

## v2.4 solver-native multi-voice harmony

- [x] Explicit soprano/alto/tenor/bass solver variables.
- [x] Voice ranges, ordering, spacing, chord completeness, and doubling policy.
- [x] Inner-voice parallel-perfect and tendency-tone resolution rules.
- [x] Independent SATB verification and artifact-provenance coverage.
- [x] Harmony no-good cuts include inner-voice realizations.

## Later

- [ ] Expanded harmonic vocabulary: sevenths, applied dominants, mixture, tonicization/modulation.
- [ ] Richer rhythmic syntax and motif transformations.
- [ ] Binary/ternary/period/form grammar.
- [ ] Transparent style profiles.
- [ ] Unsat explanations mapped back to musical rules and configuration fields.
- [ ] MusicXML export and notation-level regression fixtures.

## Neuro-symbolic track

A model may propose motifs, harmonic plans, rhythmic cells, phrase plans, or target curves, but only the symbolic layer is allowed to certify the final artifact. The intended boundary is `proposal -> compile/repair -> independent verify -> export`, not unconstrained model generation presented as verified composition.
