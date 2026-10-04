# Secondary Leading-Tone Triads — v2.10 semantics

v2.10 introduced independently certified target-bearing diminished triads (`vii°/x`). v2.11 preserves these triad semantics unchanged and adds a separate opt-in seventh family documented in [Secondary Leading-Tone Seventh Chords](SECONDARY_LEADING_TONE_SEVENTHS.md).

## Configuration

```yaml
secondary_leading_tone_enabled: true
minimum_secondary_leading_tone_chords: 1
```

The v2.10 triad switch remains independent from the v2.11 seventh switch. Enabling one does not implicitly enable the other.

## Decomposed identity

A secondary leading-tone triad is reconstructed from:

- exact active local key;
- explicit non-tonic target identity;
- `ChordKind.TRIAD`;
- deterministic support degree;
- inversion;
- SATB realization.

No opaque secondary-chord-name field exists.

## Pitch construction

For target pitch class `T`:

```text
root              = T - 1 semitone
minor third       = root + 3 semitones
diminished fifth  = root + 6 semitones
```

The exact active key is used. After a modulation boundary, that means the persistent destination key rather than the artifact-global source key.

## Support-degree compatibility bridge

The chromatic diminished root is often not an ordinary diatonic root. v2.10 therefore stores a deterministic active-key support degree chosen to preserve historical CM005/CM006/CM007 semantics.

The verifier independently recomputes that support degree from active key, target, and progression graph. It then separately verifies the actual target-derived diminished triad.

The support degree is therefore a compatibility representation, not a claim that the chromatic diminished root is diatonic.

## Realization

CM053 requires:

- the complete diminished-triad pitch set;
- local leading tone exactly once;
- diminished fifth exactly once;
- stable third doubled;
- root, first, or second inversion only;
- inversion/bass agreement;
- no arbitrary extra chromatic tone.

## Resolution

CM054 requires immediate resolution to the declared target. The destination target chord must be untargeted, unborrowed, triadic, and active-key consistent.

Tendency tones are independent:

- local leading tone rises by exactly one semitone;
- diminished fifth descends by one or two semitones.

## Interaction with applied dominants and v2.11

In v2.10, target + triad distinguished `vii°/x` from target + seventh applied dominants.

v2.11 adds target-bearing fully diminished sevenths, so **seventh form alone no longer proves applied-dominant identity**. Applied `V7/x` and secondary `vii°7/x` are now separated by exact active-key pitch/support reconstruction.

This does not alter v2.10 triad classification: a target-bearing triad under the v2.10 feature remains governed by CM052–CM054 and cannot satisfy `minimum_applied_dominants`.

## Interaction with modal mixture

A certified secondary leading-tone triad cannot simultaneously carry modal-source identity. Target identity, source identity, active key, harmonic form, and voicing remain separate axes.

## Interaction with modulation

Secondary leading-tone triads are excluded from protected cadence/modulation anchors. After the boundary, pitch construction and support-degree reconstruction use the persistent destination active key.

The v2.8.0a2 destination cadence invariants remain untouched.

## Provenance

Target identity, harmonic form, inversion, SATB voicing, modal source, active key context, and the generation specification are already committed by semantic provenance. No synthetic secondary-triad function field is required.

## Hard rules

- **CM052** — target/context/support eligibility and protected-anchor/modal-source separation.
- **CM053** — exact diminished-triad realization, multiplicities, and inversion.
- **CM054** — immediate target resolution and local tendency-tone motion.

These rules remain part of the v2.11 `CM001–CM057` contract without semantic weakening.
