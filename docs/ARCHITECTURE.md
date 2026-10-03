# Architecture

Constraint Music is deliberately split into generation, search, serialization, and independent verification paths.

```text
YAML GenerationSpec
       |
       v
 tonal/key-domain construction
       |
       +--> harmonic-form + tonicization relation tables
       |
       v
CP-SAT compiler ------------------------------------+
       |   \-> SATB + harmonic-context realization  |
       v                                             |
 feasible + optimized assignment                     |
       |                                             |
       +--> no-good enumeration / scalarization      |
       |                                             |
       v                                             |
ordinary Python musical values                       |
       |                                             |
       +--> independent objective recomputation      |
       |                                             |
       v                                             |
independent verifier <------------- hard contract ---+
       |
       +--> MIDI
       +--> verifiable JSON artifact
```

## Trust boundary

The CP-SAT model is not accepted as evidence that an output is correct. A generated assignment is converted into ordinary Python values and passed to `verify_result`. The verifier does not inspect OR-Tools variables, constraints, solver state, or internal table membership. If verification fails, generation fails closed with `InternalVerificationError`.

The same separation applies to objective metadata. Objective-component values produced inside the model are independently reconstructed from ordinary musical values; disagreement also fails closed.

## Stable hard-rule contract

`constraint_music.contract` defines stable IDs for every hard musical rule. v2.6 contains `CM001`–`CM040`.

New feasibility semantics are introduced as a synchronized change across:

1. contract metadata;
2. CP-SAT compilation;
3. independent post-solve verification;
4. adversarial regression tests;
5. artifact/provenance representation when new state is serialized.

Search mechanisms cannot waive a `CM` rule. No-good cuts constrain which already-valid assignment may be returned next; weighted scalarization ranks feasible assignments; Pareto filtering compares independently reconstructed objective vectors.

## Harmonic identity is decomposed

Constraint Music intentionally does not collapse harmony into a single display string. At v2.6, a beat's harmonic state is represented through separate axes:

- global diatonic `chord_degree`;
- `ChordKind` (`triad` or `seventh`);
- inversion (`0`, `1`, or `2`);
- nullable `tonicization_target`;
- concrete SATB notes.

Roman/slash notation is a derived presentation, not the canonical identity. For example, `V7/V` in C major is reconstructed from a global root degree, seventh kind, inversion, and target degree 5. This prevents display syntax from becoming solver state and leaves room for future local-key/modulation representation without redefining existing fields.

## SATB compiler

The SATB harmonic skeleton operates at one sonority per beat. Soprano is constrained to equal the melody at each beat's strong grid step; alto and tenor are independent solver variables; bass reuses the established beat-level bass variable.

Pitch-class variables are linked to note variables with modulo constraints. Cached allowed-assignment tables jointly constrain chord degree, chord kind, inversion, tonicization target, and four voice pitch classes. Normal triads/sevenths and applied dominants therefore use the same typed relation-table architecture rather than special post-processing.

Ordering/spacing use direct integer constraints. Parallel-perfect and tendency-tone behavior use adjacent-beat transition constraints.

## v2.6 tonicization model

Tonicization is opt-in and requires the v2.5 seventh vocabulary. `NO_TONICIZATION_TARGET` is an internal sentinel only; serialized artifacts expose `null` for ordinary global-key harmony and an integer scale degree for an applied target.

For each supported target, the tonal layer derives the applied dominant root and exact dominant-seventh pitch classes. The SATB relation table admits only complete realizations consistent with the preserved outer-voice contract.

The motion layer then requires:

- target beat exists;
- next global chord degree equals the declared target;
- next beat is not itself marked as the continuation of the same tonicization;
- the applied seventh resolves down by step;
- the target's chromatic leading tone resolves upward by semitone.

The verifier independently reconstructs the same facts from serialized notes and metadata.

## Compatibility boundary

`CM005` and `CM006` continue to interpret strong melody and bass against the global diatonic triad identified by `chord_degree`. v2.6 does not reinterpret those IDs. Applied chromatic tones are therefore carried by inner voices.

The theory layer computes which local targets are representable under that invariant. Targets that would require weakening the established outer-voice semantics are omitted from the supported target set. This is an explicit compatibility decision, not a claim that those tonicizations are musically invalid.

## Optimization

All hard musical rules remain non-negotiable. The minimized objective vector remains:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

v2.6 intentionally does not add an objective reward for tonicization. Tonicization changes feasibility/context when enabled, while search ranking remains comparable with earlier versions.

## Distinct enumeration

Exact no-good dimensions are independent:

- `melody` — melody MIDI sequence;
- `rhythm` — onset/tie/rest sequence;
- `bass` — bass MIDI sequence;
- `harmony` — global chord-degree sequence;
- `voicing` — alto/tenor realization;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable local-target sequence.

This decomposition lets callers ask for different tonicization plans without forcing different chord roots, or different voicings without claiming a different harmonic identity.

## Pareto approximation

Pareto mode explores a deterministic family of weighted scalarizations, applies exact no-good cuts to keep candidates distinct, independently reconstructs each objective vector, and removes dominated candidates from the explored pool. Because the pool is bounded, the result is an approximation of the global Pareto frontier.

## Extension boundary

Future modal mixture and modulation should add explicit source/mode/local-key identity rather than treating non-diatonic pitch classes as globally permitted. The v2.6 separation between global chord identity and local target context is intended to make that extension possible without mutating earlier artifacts or rule meanings.
