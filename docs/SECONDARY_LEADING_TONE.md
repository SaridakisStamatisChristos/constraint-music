# Secondary Leading-Tone Chords

Constraint Music v2.10 adds a deliberately narrow, independently verifiable model of secondary leading-tone triads (`vii°/x`). The feature is opt-in and does not enable unrestricted chromatic harmony.

```yaml
secondary_leading_tone_enabled: true
minimum_secondary_leading_tone_chords: 1
```

## Semantic identity

v2.10 does not add an opaque Roman-numeral or chromatic-root field. It composes existing typed state:

- the exact active local key;
- a nullable local target degree;
- `ChordKind.TRIAD`;
- inversion;
- a functional/support degree retained for the legacy progression/outer-voice contract;
- the concrete SATB realization.

The same target field remains used by applied dominants. Harmonic form separates the two certified functions:

- target + `ChordKind.SEVENTH` -> applied dominant (`V7/x`);
- target + `ChordKind.TRIAD` -> secondary leading-tone chord (`vii°/x`).

This keeps target identity orthogonal to harmonic form and avoids synthetic replacement metadata.

## Target-derived pitch content

For a supported target degree `x`, let `T` be the target root pitch class in the exact active local key. The secondary leading-tone triad is reconstructed as:

```text
root              = T - 1 semitone
minor third       = root + 3 semitones
diminished fifth  = root + 6 semitones
```

The target must be a non-tonic diatonic major or minor triad. Targets that cannot coexist with the established functional progression and outer-voice contract are structurally excluded.

## Why there is a support degree

A chromatic secondary leading-tone root is not necessarily a diatonic scale degree. Constraint Music therefore does **not** pretend that the chromatic root is an ordinary diatonic chord degree.

The serialized `chord_degree` is instead a deterministic active-key **support degree**. A support degree must:

1. already be permitted by the configured progression graph to move to the declared target;
2. share at least two pitch classes with the target-derived diminished triad;
3. maximize that shared pitch content, with deterministic lowest-degree tie breaking.

This support identity preserves the established meanings of:

- `CM005` — strong melody/soprano belongs to the active-key triadic core;
- `CM006` — bass belongs to the active-key triadic core;
- `CM007` — the functional degree transition is admitted by the configured progression graph.

It is a compatibility bridge, not the theoretical root of the chromatic sonority. The verifier independently reconstructs the real diminished chord from active key + target.

## Certified SATB realization

A secondary leading-tone chord must contain exactly the three target-derived pitch classes. In the four SATB voices:

- the local leading-tone root appears exactly once;
- the diminished fifth appears exactly once;
- the stable minor third is doubled;
- root, first, and second inversion are supported;
- the serialized inversion must agree with the realized bass pitch class.

The tendency tones are intentionally not doubled so their required motion remains explicit and independently checkable.

## Resolution semantics

The chord resolves immediately to its declared target. The target sonority must be:

- the declared diatonic target degree;
- `ChordKind.TRIAD`;
- untargeted on the resolution beat;
- unborrowed on the resolution beat.

Every SATB voice carrying the local leading tone must rise by exactly one semitone. Every voice carrying the diminished fifth must descend by one or two semitones.

These are solver-native constraints and independent verifier checks.

## Interaction with applied dominants

Secondary leading-tone chords reuse target identity but do not count as applied dominants. `minimum_applied_dominants` counts target-bearing sevenths only. Conversely, `minimum_secondary_leading_tone_chords` counts target-bearing triads only.

This means a target-bearing triad cannot counterfeit the applied-dominant requirement merely because both functions point to the same local tonic.

## Interaction with modal mixture

A secondary leading-tone chord cannot simultaneously carry modal-source identity. The target chord on the following beat must also be unborrowed.

This prevents a single beat from acquiring two incompatible chromatic explanations and keeps source identity independent from target identity.

## Interaction with modulation

Persistent local-key context remains authoritative. Before the modulation boundary, the diminished triad is derived from the source active key. From the boundary onward, it is derived from the destination active key.

The original artifact/global key is never reused as stale post-modulation context.

Secondary leading-tone chords are excluded from the certified source/pivot anchor and the terminal destination cadence anchors. v2.10 therefore does not weaken the v2.8.0a2 strict destination-cadence guarantee.

## Hard rules

v2.10 adds three rules:

- `CM052` — secondary leading-tone context: supported target, deterministic support degree, no modal overlap, no protected-anchor overlap;
- `CM053` — exact diminished realization: complete pitch content, tendency tones undoubled, stable third doubled, inversion/bass agreement;
- `CM054` — target/tendency resolution: immediate unaltered target, leading tone up by semitone, diminished fifth down by step.

The solver and verifier implement these semantics separately. Any disagreement fails closed.

## Provenance

No new opaque semantic field is required. Artifact schema/contract 2.10 commits the existing specification and musical metadata, including target identity, harmonic form, inversion, SATB voicing, modal source, and persistent key context where present.

Changing a secondary target or any other committed semantic identity changes the composition/artifact digest and is detectable during offline verification.

## Explicit non-goals

v2.10 does not certify:

- secondary leading-tone seventh chords;
- third-inversion sevenths;
- free chromatic roots outside the supported target model;
- arbitrary modulation chains;
- distant/enharmonic reinterpretation;
- augmented-sixth or Neapolitan reinterpretation;
- probabilistic key inference.

Those require explicit future contract versions rather than silent reinterpretation of v2.10 semantics.
