# Secondary Leading-Tone Seventh Chords — v2.11

v2.11 extends Constraint Music's target-bearing chromatic-function model with independently certified **fully diminished secondary leading-tone seventh chords**.

The extension is deliberately narrow. It is additive to v2.10 secondary leading-tone triads and does not silently widen older seventh-chord semantics.

## Enable the feature

```yaml
harmony_vocabulary: triads+sevenths
secondary_leading_tone_seventh_enabled: true
minimum_secondary_leading_tone_seventh_chords: 1
```

The v2.10 triad switch remains separate:

```yaml
secondary_leading_tone_enabled: true
```

Enabling the v2.11 seventh feature does not implicitly enable v2.10 triads.

## Certified quality policy

v2.11 certifies only the **fully diminished seventh** family:

```text
vii°7/x
vii°65/x
vii°43/x
```

Half-diminished secondary leading-tone sevenths are intentionally outside the v2.11 contract. Third inversion is also outside the contract.

For a declared target pitch class `T`, the certified pitch-class set is reconstructed as:

```text
root              = T - 1 semitone
minor third       = root + 3 semitones
diminished fifth  = root + 6 semitones
diminished seventh= root + 9 semitones
```

All arithmetic is modulo 12 and uses the **active local key** at the beat.

## Identity is decomposed, not opaque

No serialized `secondary_chord_name` field exists. Identity is reconstructed from existing orthogonal fields:

- active key context;
- local target identity;
- chord kind (`SEVENTH`);
- support degree;
- inversion;
- modal source;
- realized SATB pitch classes.

This matters because target-bearing sevenths now have two possible certified families:

1. exact applied dominant `V7/x`;
2. exact fully diminished secondary leading-tone seventh `vii°7/x`.

A beat counts as an applied dominant only when its active-key root/support identity, exact four pitch classes, and inversion reconstruct as `V7/x`. Merely carrying a target and `ChordKind.SEVENTH` is not sufficient.

## Support-degree compatibility bridge

The actual diminished root is chromatic and is not represented as a fake diatonic chord degree.

Instead, v2.11 derives a deterministic active-key **support degree** that:

- is already allowed to progress to the declared target by the configured progression graph;
- shares at least two pitch classes with the chromatic seventh sonority;
- maximizes overlap, with deterministic tie-breaking.

This preserves the established meanings of CM005, CM006, and CM007 while target metadata and SATB voicing carry the chromatic functional identity.

## Realization

CM056 requires:

- all four fully diminished pitch classes exactly once;
- no duplicated unstable tone;
- root, first, or second inversion only;
- serialized inversion agreeing with the realized bass;
- no arbitrary extra chromatic pitch.

The outer soprano/bass compatibility policy remains tied to the support triad so historical CM005/CM006 semantics are not silently redefined.

## Resolution

CM057 requires immediate resolution to the declared target. The destination chord must be:

- untargeted;
- unborrowed;
- triadic;
- consistent with the active local key.

Tendency tones are reconstructed independently in every SATB voice:

- local leading tone: **up by semitone**;
- diminished fifth: **down by one or two semitones**;
- chordal diminished seventh: **down by one or two semitones**.

These requirements are compiler constraints and independent verifier checks.

## Interaction with applied dominants

`minimum_applied_dominants` counts only exact applied `V7/x` realizations.

A v2.11 secondary leading-tone seventh cannot satisfy that minimum even though it is target-bearing and seventh-form. Conversely, a valid applied dominant is not reclassified as a secondary leading-tone seventh.

The distinction is reconstructed from musical values, not a synthetic function flag stored in the artifact.

## Interaction with modal mixture

A certified secondary leading-tone seventh cannot simultaneously carry modal-source identity.

Target identity, modal source, harmonic form, persistent key context, and voicing remain independent axes. The verifier rejects overlap rather than treating one metadata field as permission to reinterpret another.

## Interaction with modulation

After a v2.8 modulation boundary, v2.11 reconstructs secondary leading-tone sevenths from the persistent **destination active key**.

It never falls back to the immutable artifact-global key.

The feature is excluded from protected modulation/cadence anchors, preserving:

- the common-chord pivot invariant;
- strict destination V-I confirmation;
- destination leading-tone presence;
- upward semitone destination-leading-tone resolution;
- exact active-key pitch admission.

## Provenance

v2.11 introduces no opaque provenance field. The semantic digest already commits the values needed to reconstruct identity:

- target identity;
- harmonic form;
- inversion;
- SATB voicing;
- modal source;
- persistent key context;
- specification feature flags and minima.

Changing any of those values invalidates semantic/artifact integrity and/or musical verification.

## Hard rules

v2.11 adds three hard rules after CM054:

- **CM055 — secondary leading-tone seventh context**: supported target, active-key support identity, fully diminished quality policy, no modal overlap, no protected-anchor contamination, and independent applied-dominant classification.
- **CM056 — secondary leading-tone seventh realization**: exact four-tone fully diminished realization and root/first/second inversion agreement.
- **CM057 — secondary leading-tone seventh resolution**: immediate target resolution plus local leading-tone, diminished-fifth, and diminished-seventh tendencies.

The certified contract is therefore `CM001–CM057`.

## Explicit non-goals

v2.11 does not certify:

- half-diminished `viiø7/x`;
- third-inversion seventh chords;
- arbitrary enharmonic reinterpretation;
- augmented-sixth or Neapolitan reinterpretation;
- distant/enharmonic modulation;
- arbitrary modulation chains;
- probabilistic or inferred chromatic-function labels.

Those require separate explicitly versioned boundaries rather than silent widening of v2.11.
