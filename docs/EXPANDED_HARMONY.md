# Expanded Harmony — v2.5

v2.5 expands the solver-native SATB layer without changing the meaning of earlier contracts.

## Compatibility first

Existing specifications remain triadic because the default is:

```yaml
harmony_vocabulary: triads
minimum_seventh_chords: 0
```

Enable v2.5 expanded harmony explicitly:

```yaml
harmony_vocabulary: triads+sevenths
minimum_seventh_chords: 1
```

`minimum_seventh_chords` is a hard lower bound. The final beat cannot be a seventh chord because every chordal seventh must have a following sonority in which to resolve.

## Harmonic identity

A v2.5 realized harmonic form has three structured components:

1. scale-relative chord degree (`0..6`), which preserves the historical harmony identity;
2. chord kind (`triad` or `seventh`);
3. inversion (`0`, `1`, or `2`).

The serialized artifact stores `chord_degrees`, `chord_kinds`, and `chord_inversions`; display-only Roman-numeral names are derived from these values.

The search dimensions are intentionally separated:

- `harmony` means chord-degree-sequence distinctness exactly as in v2.3/v2.4;
- `voicing` means alto/tenor realization distinctness;
- `harmonic_form` means chord-kind/inversion distinctness.

Therefore v2.5 does not silently change an existing no-good dimension.

## Supported seventh chords

The first v2.5 boundary supports complete **diatonic seventh chords** built from scale degrees 1-3-5-7 relative to the chord root. In four-part SATB every seventh chord contains all four chord tones exactly once.

CM005 and CM006 retain their v2.4 meanings: strong melody and bass are members of the active triadic core. Consequently, the new chordal seventh is carried by alto or tenor, and v2.5 supports root, first, and second inversion only. Third inversion is intentionally deferred rather than obtained by redefining the old bass rule.

## Resolution semantics

Every voice carrying a chordal seventh must move downward by diatonic step into the next sonority. In the supported major/harmonic-minor scales this is encoded as one or two semitones downward.

A dominant seventh has additional hard semantics:

- degree `V7` resolves to degree `I`;
- every SATB voice carrying the key leading tone resolves upward by semitone.

These are compiled into CP-SAT and recomputed independently from serialized SATB notes.

## New hard rules

- **CM033 — harmonic-form shape:** kind/inversion arrays cover every beat and comply with vocabulary/minimum-seventh declarations.
- **CM034 — expanded chord realization:** seventh chords contain four distinct chord tones, and serialized inversion agrees with the realized bass.
- **CM035 — chordal seventh resolution:** every chordal seventh has a following sonority and resolves downward by step.
- **CM036 — dominant seventh resolution:** every V7 resolves to tonic and every V7 leading-tone carrier resolves upward by semitone.

CM001–CM032 retain their established meanings.

## Artifact and provenance semantics

Artifact schema `2.5` includes harmonic form in semantic provenance when the metadata is present. Tampering with `chord_kinds` or `chord_inversions` changes the semantic composition digest and artifact-content digest.

Older SATB payloads that do not contain these arrays still load. The loader does not invent them merely to make an old artifact resemble schema 2.5.

## Deliberate exclusions

v2.5 does **not** claim support for secondary dominants, borrowed chords, modal mixture, tonicization, local-key contexts, pivot chords, or modulation. Those features require a chromatic/local-key representation and their own independently falsifiable contracts before they can be called verified.
