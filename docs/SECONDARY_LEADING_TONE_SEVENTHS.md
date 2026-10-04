# Secondary Leading-Tone Seventh Chords — v2.12

v2.12 completes Constraint Music's verifier-certified secondary leading-tone seventh subsystem within the declared common-practice tonicization domain. The implementation no longer treats half-diminished quality or third inversion as deferred convenience cases.

## Enable the feature

```yaml
harmony_vocabulary: triads+sevenths
secondary_leading_tone_seventh_enabled: true
minimum_secondary_leading_tone_seventh_chords: 1
```

The secondary-leading-tone triad switch remains independent:

```yaml
secondary_leading_tone_enabled: true
```

When the seventh feature is disabled, the pre-v2.12 feasible set and verifier path remain unchanged.

## Certified family

For a major target triad, v2.12 certifies both:

```text
vii°7/x   vii°65/x   vii°43/x   vii°42/x
viiø7/x   viiø65/x   viiø43/x   viiø42/x
```

For a minor target triad, v2.12 certifies the fully diminished family only:

```text
vii°7/x   vii°65/x   vii°43/x   vii°42/x
```

Diminished and augmented targets remain outside secondary tonicization.

For target pitch class `T`, the common lower structure is:

```text
root              = T - 1 semitone
minor third       = root + 3 semitones
diminished fifth  = root + 6 semitones
```

The seventh is quality-specific:

```text
fully diminished: root + 9 semitones
half diminished:  root + 10 semitones
```

All arithmetic is modulo 12 and is evaluated against the active local key at the beat.

## Identity is reconstructed, never trusted

No opaque function label is serialized. The verifier independently reconstructs identity from:

- the active local key;
- the declared tonicization target;
- chord kind;
- deterministic progression-support degree;
- SATB pitch classes;
- bass/inversion agreement;
- modal-source absence.

A target-bearing seventh is therefore not automatically classified as an applied dominant or a secondary leading-tone seventh. Exact musical identity decides the function.

Applied `V7/x`, fully diminished `vii°7/x`, and eligible half-diminished `viiø7/x` remain disjoint certified families.

## Chromatic outer voices

v2.11 still inherited a diatonic outer-voice shortcut from CM005/CM006. That shortcut prevented a genuinely chromatic member from appearing in the soprano or bass and made `42` impossible to certify correctly.

v2.12 replaces that shortcut only on the secondary-seventh execution path:

- ordinary beats retain the historical diatonic outer-voice domains;
- a strong secondary-seventh beat may admit one of the exact target-derived chromatic chord tones;
- CM005/CM006 use the deterministic support degree for progression compatibility while the realized seventh supplies the exact chord-member set;
- the independent verifier grants the chromatic exception only after exact secondary-seventh reconstruction.

A malformed target-bearing chord therefore does not inherit a broad chromatic exemption. It falls back under CM002/CM003/CM005/CM006 and also fails CM055/CM056 as applicable.

## Support-degree compatibility bridge

The chromatic functional root is not encoded as a fake diatonic degree. A deterministic support degree is chosen from the active key such that it:

- is already allowed to progress to the target by the configured progression graph;
- shares at least two pitch classes with the chromatic sonority;
- maximizes pitch-class overlap;
- breaks ties deterministically.

CM007 thus retains its historical progression-graph meaning while target metadata and exact SATB realization carry the chromatic function.

## Realization — CM056

Every certified secondary leading-tone seventh must contain exactly one instance of each of its four target-derived pitch classes.

The verifier admits all four inversion figures:

```text
0 -> 7
1 -> 65
2 -> 43
3 -> 42
```

The serialized inversion must agree with the actual bass pitch class. Third inversion is not merely a metadata value: the chordal seventh must actually be in the bass.

## Resolution — CM057

Every certified secondary leading-tone seventh resolves immediately to its declared target. The destination must be:

- untargeted;
- unborrowed;
- triadic;
- interpreted in the same active local-key context.

The tendency rules are exact rather than range-based:

- local leading tone/root: `+1` semitone;
- diminished fifth: `-1` semitone for a major target, `-2` for a minor target;
- fully diminished chordal seventh: `-1` semitone;
- half-diminished chordal seventh: `-2` semitones.

These deltas are compiled into CP-SAT and independently recomputed by the verifier. They apply to whichever SATB voice carries the tendency tone, including the bass in `vii°42/x` and `viiø42/x`.

## Applied-dominant separation

`minimum_applied_dominants` counts only exact reconstructed `V7/x` chords. A secondary leading-tone seventh cannot satisfy that minimum merely because it carries a target and has seventh form.

Conversely, an exact applied dominant is excluded from secondary-leading-tone classification before quality reconstruction.

## Modal mixture and protected anchors

A secondary leading-tone seventh cannot simultaneously carry modal-source identity. Certified cadence and modulation anchors remain protected from local chromatic-function substitution.

After a modulation boundary, every secondary seventh is reconstructed against the persistent destination active key. The immutable source key is never used as a stale fallback.

## Provenance

No new opaque quality/function field is required in the artifact. The existing semantic digest commits the data from which the function is reconstructed:

- target identity;
- harmonic form;
- inversion;
- SATB voicing;
- modal source;
- persistent key context;
- feature flags and minima.

Tampering with any of those values changes the semantic/artifact digest and/or fails musical verification.

## Hard-rule contract

v2.12 keeps the 57-rule surface but strengthens CM002/CM003/CM005/CM006 and CM055–CM057 rather than inventing redundant rule IDs.

- **CM055 — secondary leading-tone seventh context**: exact active-key target/support identity, quality eligibility, no applied/modal overlap, and protected-anchor exclusion.
- **CM056 — secondary leading-tone seventh realization**: exact four-tone fully diminished or eligible half-diminished realization, with all four inversions and bass agreement.
- **CM057 — secondary leading-tone seventh resolution**: immediate target resolution plus exact target- and quality-dependent tendency motion in every SATB voice.

The certified contract remains `CM001–CM057`, versioned as **2.12**.

## Deliberate boundaries that remain

v2.12 does not claim arbitrary chromatic harmony. It still excludes:

- diminished or augmented tonicization targets;
- enharmonic respelling as a substitute for functional identity;
- augmented-sixth or Neapolitan reinterpretation;
- distant/enharmonic modulation and arbitrary modulation chains;
- probabilistic or inferred function labels.

Those are separate harmonic domains. They are not omissions from the secondary leading-tone seventh family certified here.
