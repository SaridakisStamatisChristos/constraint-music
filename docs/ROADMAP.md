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

- [ ] Replace seed variation as the primary alternative-generation mechanism with CP-SAT no-good cuts.
- [ ] Allow explicit distinctness dimensions such as melody, rhythm, bass, and harmony.
- [ ] Add objective-vector metadata.
- [ ] Add weighted scalarization and/or Pareto-front approximation.
- [ ] Test deterministic enumeration and Pareto dominance independently.

## v2.4 solver-native multi-voice harmony

- [ ] Explicit soprano/alto/tenor/bass solver variables.
- [ ] Voice ranges, ordering, spacing, chord completeness, and doubling policy.
- [ ] Inner-voice parallel-perfect and tendency-tone resolution rules.

## Later

- [ ] Expanded harmonic vocabulary: sevenths, applied dominants, mixture, tonicization/modulation.
- [ ] Richer rhythmic syntax and motif transformations.
- [ ] Binary/ternary/period/form grammar.
- [ ] Transparent style profiles.
- [ ] Unsat explanations mapped back to musical rules and configuration fields.
- [ ] MusicXML export and notation-level regression fixtures.

## Neuro-symbolic track

A model may propose motifs, harmonic plans, rhythmic cells, phrase plans, or target curves, but only the symbolic layer is allowed to certify the final artifact. The intended boundary is `proposal -> compile/repair -> independent verify -> export`, not unconstrained model generation presented as verified composition.
