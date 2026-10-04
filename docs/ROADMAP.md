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

## v2.7 verified modal mixture

- [x] Explicit nullable per-beat source-mode identity.
- [x] Canonical parallel source policy: natural minor for active major, major for active minor.
- [x] Source-derived borrowed triads with no unrestricted chromatic pitch permission.
- [x] Structural filtering of borrowed degrees incompatible with preserved CM005/CM006 semantics.
- [x] Preserve certified cadence/context anchors while allowing borrowing elsewhere.
- [x] Make modal mixture and tonicization mutually exclusive at a beat.
- [x] Independent CM041–CM042 verifier symmetry and adversarial tamper tests.
- [x] `modal_source` distinctness without redefining existing search dimensions.
- [x] Schema/contract 2.7 provenance for modal-source metadata.

## v2.8 persistent local key and controlled modulation

- [x] Persistent active local-key state distinct from one-chord tonicization.
- [x] One explicit same-mode dominant-key modulation event.
- [x] Explicit destination-key identity and modulation boundary.
- [x] Fixed common-chord pivot: source I reinterpreted as destination IV.
- [x] Persistent destination-key interpretation after the boundary.
- [x] Destination-key V-I confirmation.
- [x] Per-beat key-context serialization and provenance commitment.
- [x] `key_context` distinctness without redefining earlier search axes.
- [x] Active-key-aware tonicization, modal mixture, objective scoring, melody, and bass checks.
- [x] Context-union storage domains plus exact per-step active-key admission.
- [x] v2.8.0a2 strict cadence repair: no terminal CM032 exemption; every destination-leading-tone carrier resolves upward.
- [x] Independent CM043–CM048 verification and hostile modulation tamper tests.

## v2.9 source-aware borrowed seventh chords

- [x] Compose expanded harmony, modal-source identity, and persistent active-key context.
- [x] Admit only a narrow source-derived borrowed-seventh whitelist compatible with CM005/CM006.
- [x] Preserve root, first, and second inversions; keep third inversion deferred.
- [x] Require complete four-tone realization and inversion/bass agreement.
- [x] Require source-aware chordal-seventh and source-leading-tone resolution.
- [x] Keep borrowing and tonicization mutually exclusive on the same beat.
- [x] Exclude certified modulation pivot and destination-cadence anchors.
- [x] Reconstruct post-modulation borrowing from the destination active key, never stale global context.
- [x] Preserve orthogonal `modal_source`, `harmonic_form`, and `key_context` search identities.
- [x] Extend the hard contract additively with CM049–CM051 and schema/contract 2.9.
- [x] Add hostile solver/verifier/provenance/cross-feature tests.

## v2.10 verified secondary leading-tone chords

- [x] Add explicit opt-in secondary leading-tone harmony without a new opaque chord identity axis.
- [x] Reuse local target identity and disambiguate applied dominants vs. leading-tone chords by harmonic form.
- [x] Derive diminished triads from the exact active local key and declared non-tonic target.
- [x] Preserve CM005/CM006/CM007 through a deterministic active-key support degree instead of forging a diatonic chromatic root.
- [x] Require complete diminished-triad realization with tendency tones undoubled and the stable third doubled.
- [x] Require immediate resolution to the declared unaltered triadic target.
- [x] Require local leading tone up by semitone and diminished fifth down by step.
- [x] Keep secondary chords disjoint from modal borrowing and certified modulation/cadence anchors.
- [x] Reconstruct post-modulation secondary harmony from the destination active key, never stale global context.
- [x] Prevent target-bearing triads from satisfying the applied-dominant minimum.
- [x] Extend the hard contract additively with CM052–CM054 and schema/contract 2.10.
- [x] Add hostile solver/verifier/provenance/post-modulation tests.

## Later harmonic expansion

- [ ] Secondary leading-tone seventh chords only after an explicit seventh-form/tendency contract revision.
- [ ] Third-inversion seventh support only after an explicit outer-voice compatibility revision.
- [ ] Richer voice-leading policy where justified by an explicit contract version.
- [ ] Multi-modulation chains only after single-modulation invariants remain stable.
- [ ] Distant-key networks and enharmonic reinterpretation.
- [ ] Augmented-sixth and Neapolitan reinterpretation.

## Later general work

- [ ] Richer rhythmic syntax and motif transformations.
- [ ] Binary/ternary/larger form grammar.
- [ ] Transparent style profiles.
- [ ] Unsat explanations mapped back to musical rules and configuration fields.
- [ ] MusicXML export and notation-level regression fixtures.

## Neuro-symbolic track

A model may propose motifs, harmonic plans, rhythmic cells, phrase plans, local targets,
modal-source plans, modulation plans, or target curves, but only the symbolic layer may certify
the final artifact. The intended boundary remains:

```text
proposal -> compile / repair -> independent verify -> export
```

Unconstrained model generation is never presented as a verified composition.
