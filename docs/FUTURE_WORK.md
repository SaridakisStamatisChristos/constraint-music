# Future Work

This document contains **unimplemented directions only**. It is deliberately separate from the README so future ideas are not confused with current Constraint Music capabilities.

## Harmonic expansion

Potential future contract revisions may explore:

- richer borrowed-seventh inversion and source policies;
- broader general seventh-chord voice-leading policies;
- multiple persistent modulation events after the single-modulation invariants remain stable;
- distant-key networks and enharmonic reinterpretation;
- augmented-sixth and Neapolitan reinterpretation;
- broader chromatic-function inference.

Any such expansion should remain opt-in, versioned, independently verifiable, and backward-compatible with earlier contract semantics unless an explicit breaking revision is declared.

## Rhythmic and formal structure

Potential future work includes:

- richer rhythmic syntax and motif transformations;
- binary, ternary, and larger formal grammars;
- additional phrase-relation families;
- notation-level regression fixtures.

## Diagnostics and interoperability

Possible engineering directions include:

- unsatisfiable-core or explanation tooling mapped back to musical rules and configuration fields;
- MusicXML export;
- clearer machine-readable diagnostic localization;
- additional independently specified delivery formats.

## Style and proposal layers

Transparent style profiles may be explored as proposal or ranking layers, but they must not weaken the hard-constraint contract.

A neuro-symbolic proposal layer may suggest motifs, harmonic plans, rhythmic cells, phrase plans, local targets, modal-source plans, modulation plans, or target curves. The symbolic boundary remains:

```text
proposal -> compile / repair -> independent verify -> export
```

Unconstrained model output should never be presented as a verified composition merely because it was proposed by a learned model.

## Research requirements

New comparative or publication claims should use prospectively declared protocols, preserve negative results, separate development data from held-out evaluation, retain exact dependency and source provenance, and avoid converting finite conformance evidence into general aesthetic or superiority claims.
