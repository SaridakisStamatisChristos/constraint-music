# Architecture

Constraint Music is deliberately split into generation, search, serialization, and independent verification paths.

```text
YAML GenerationSpec
       |
       v
 tonal/key-domain construction
       |
       +--> harmonic-form + tonicization + modal-source relation tables
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

`constraint_music.contract` defines stable IDs for every hard musical rule. v2.7 contains `CM001`–`CM042`.

New feasibility semantics are introduced as a synchronized change across contract metadata, CP-SAT compilation, independent post-solve verification, adversarial regression tests, and artifact/provenance representation whenever new state is serialized.

Search mechanisms cannot waive a `CM` rule. No-good cuts constrain which already-valid assignment may be returned next; weighted scalarization ranks feasible assignments; Pareto filtering compares independently reconstructed objective vectors.

## Harmonic identity is decomposed

Constraint Music intentionally does not collapse harmony into a display string. At v2.7, each beat can carry separate axes:

- global functional `chord_degree`;
- `ChordKind` (`triad` or `seventh`);
- inversion (`0`, `1`, or `2`);
- nullable `tonicization_target`;
- nullable `modal_source`;
- concrete SATB notes.

Roman/slash/source notation is derived presentation rather than canonical identity. `V7/V` is reconstructed from global root degree, seventh kind, inversion, and target degree. A borrowed `iv[parallel_natural_minor]` is reconstructed from global functional degree, triad kind, inversion, and explicit source mode.

## SATB compiler

The SATB harmonic skeleton operates at one sonority per beat. Soprano equals the melody at each beat's strong grid step; alto and tenor are independent solver variables; bass reuses the established beat-level bass variable.

Pitch-class variables are linked to note variables with modulo constraints. Cached allowed-assignment tables jointly constrain chord degree, chord kind, inversion, tonicization target, modal source, and four voice pitch classes. Global triads/sevenths, applied dominants, and borrowed triads therefore use the same typed relation-table architecture instead of post-processing exceptions.

Ordering/spacing use direct integer constraints. Parallel-perfect and seventh/tendency-tone behavior use adjacent-beat transition constraints.

## v2.6 tonicization model

Tonicization remains opt-in and requires the seventh vocabulary. `NO_TONICIZATION_TARGET` is internal only; serialized artifacts expose `null` for global harmony and an integer scale degree for an applied target.

For each supported target, the tonal layer derives the applied dominant root and exact dominant-seventh pitch classes. The SATB relation table admits only complete realizations compatible with the preserved outer-voice contract. Motion constraints require immediate target resolution, downward applied-seventh resolution, and upward local-leading-tone resolution. The verifier reconstructs those consequences from serialized values.

## v2.7 modal-mixture model

Modal mixture is an independent opt-in context axis. `NO_MODAL_SOURCE` is an internal sentinel; serialized artifacts use `null` for global harmony and an explicit source label for borrowed harmony.

The canonical source policy is deliberately small:

- global major -> parallel natural minor;
- global minor -> parallel major.

For a borrowed beat, the theory layer derives the source scale from the global tonic, builds the source triad on the stored functional degree, and admits only complete SATB realizations of that triad. A borrowed beat is triadic in v2.7 and cannot also carry a tonicization target.

The final beat remains global. With authentic closure enabled, the penultimate beat remains global as well. This keeps earlier cadence semantics stable.

## Compatibility boundary

`CM005` and `CM006` continue to interpret strong melody and bass against the global diatonic triad identified by `chord_degree`. Neither tonicization nor mixture reinterprets these IDs. Chromatic applied or borrowed tones are therefore carried by inner voices.

The theory layer exposes only harmonic contexts representable under that invariant. This is an explicit compatibility decision rather than a claim that omitted harmonies are invalid in music theory.

Borrowed triads receive their own source-derived completeness rule (`CM042`) rather than weakening global-triad root-doubling (`CM030`). Borrowed sevenths are deferred because they need source-aware seventh/tendency semantics rather than silently inheriting global CM035/CM036 behavior.

## Optimization

All hard musical rules remain non-negotiable. The minimized objective vector remains:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

v2.7 intentionally adds no reward or penalty for modal mixture. Mixture changes the feasible/contextual space when enabled while objective ranking remains comparable with earlier versions.

## Distinct enumeration

Exact no-good dimensions are independent:

- `melody` — melody MIDI sequence;
- `rhythm` — onset/tie/rest sequence;
- `bass` — bass MIDI sequence;
- `harmony` — global chord-degree sequence;
- `voicing` — alto/tenor realization;
- `harmonic_form` — chord kind + inversion;
- `tonicization` — nullable local-target sequence;
- `modal_source` — nullable parallel-source sequence.

This decomposition allows two outputs to share functional roots while differing only in tonicization, borrowing, form, or voicing.

## Pareto approximation

Pareto mode explores a deterministic family of weighted scalarizations, applies exact no-good cuts to keep candidates distinct, independently reconstructs each objective vector, and removes dominated candidates from the explored pool. Because the pool is bounded, the result is an approximation of the global Pareto frontier.

## Extension boundary

Future chromatic expansion should continue to add typed context rather than globally permitting altered pitch classes. Secondary leading-tone chords need explicit tendency semantics; persistent local-key regions need local-key identity; modulation needs destination and pivot identity. Third-inversion sevenths require an explicit revision of the preserved outer-voice contract rather than a silent reinterpretation.
