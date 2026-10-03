# Roadmap

## v2 foundation

- [x] Recover v1.1 CP-SAT generator behavior.
- [x] Version the hard-constraint contract.
- [x] Complete independent verification of solver hard rules.
- [x] Fail closed on solver/verifier disagreement.
- [x] Add verifiable JSON provenance.
- [x] Add offline `verify` command.

## Next: expressive symbolic composition

- [ ] Rhythm CSP: onsets, ties, rests, durations, syncopation, metrical accents.
- [ ] Motif and phrase grammar: repetition, transposition, sequence, antecedent/consequent structure.
- [ ] Species-counterpoint module with explicit dissonance treatment.
- [ ] Four-part SATB voicing and voice-leading constraints.
- [ ] Multi-objective/Pareto solution enumeration rather than one weighted objective.
- [ ] Unsat explanations mapped back to musical rules and configuration fields.
- [ ] MusicXML export and notation-level regression fixtures.

## Later: neuro-symbolic mode

A model may propose motifs, harmonic plans, or target curves, but only the symbolic layer is allowed to certify the final artifact. The intended boundary is `proposal -> compile/repair -> independent verify -> export`, not unconstrained model generation presented as verified composition.
