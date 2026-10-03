# Applied-Dominant Tonicization

Constraint Music v2.6 adds a bounded, independently verifiable tonicization model based on applied dominant sevenths.

## Design goal

The release introduces local dominant function without pretending that a one-chord tonicization is a permanent key change and without granting unrestricted chromatic pitch access.

Global key identity, global chord degree, chord kind, inversion, local tonicization target, and SATB voicing remain separate data.

## Configuration

Tonicization is opt-in and requires the v2.5 seventh-chord vocabulary:

```yaml
harmony_vocabulary: triads+sevenths
tonicization_enabled: true
minimum_applied_dominants: 1
```

`minimum_applied_dominants` counts beats whose serialized `tonicization_target` is non-null. An applied dominant cannot occupy the final beat because its target resolution is part of the hard contract.

## Semantic representation

Ordinary harmony has:

```text
chord_degree = d
chord_kind = triad | seventh
inversion = 0 | 1 | 2
tonicization_target = null
```

An applied dominant adds a target:

```text
chord_degree = global diatonic degree of applied-dominant root
chord_kind = seventh
inversion = 0 | 1 | 2
tonicization_target = target scale degree
```

Roman-numeral strings such as `V7/V` are derived display values. They are not canonical solver state.

## Pitch construction

For target scale degree `t` in global key `K`:

1. resolve the target pitch class from `K`;
2. place the applied-dominant root a perfect fifth above that target;
3. construct a dominant seventh above the root with intervals `0, 4, 7, 10` semitones;
4. require the SATB realization to contain those four pitch classes exactly once.

In C major, target degree 5 is G. Its applied dominant is D7 with pitch classes D-F#-A-C, displayed as `V7/V` in root position.

## Target support and backward compatibility

`CM005` and `CM006` predate chromatic harmony and retain their established meanings: strong melody/soprano and bass must belong to the global diatonic triad identified by the beat's global chord degree.

v2.6 does not redefine those rules. Instead, the tonal layer computes a supported-target set for which a complete applied dominant can be realized while soprano and bass remain compatible with that older triadic-core contract. Chromatic applied tones are carried by alto/tenor.

This means the set of exposed targets depends on the global key/mode and the preserved representation contract. A missing target is a compatibility limitation of v2.6, not a music-theory claim that the tonicization is invalid.

## Resolution contract

Every applied dominant must resolve on the immediately following beat:

```text
beat n:     tonicization_target = t
beat n + 1: chord_degree = t
            tonicization_target = null
```

The applied chordal seventh resolves downward by step: `-1` or `-2` semitones.

The applied dominant's major third functions as the local leading tone and resolves upward by exactly one semitone. Both rules are checked in whichever SATB voice carries the tendency tone.

## Hard-rule IDs

v2.6 adds:

- `CM037` — tonicization-context shape, eligibility, and minimum-count semantics;
- `CM038` — target-derived applied-dominant realization and inversion consistency;
- `CM039` — immediate resolution to the declared untargeted local tonic;
- `CM040` — applied seventh and local-leading-tone resolution.

The solver compiles these requirements and the independent verifier reconstructs them from serialized notes/metadata.

## Distinct enumeration

`tonicization` is a separate no-good dimension:

```bash
constraint-music generate examples/applied_dominants.yaml \
  --count 3 \
  --distinct-on tonicization,voicing \
  --output build/variant.mid \
  --json build/variant.json
```

This preserves the earlier meanings:

- `harmony`: global chord-degree sequence;
- `harmonic_form`: chord kind + inversion;
- `voicing`: alto + tenor pitches.

## Provenance

Artifact schema/contract 2.6 commits `tonicization_targets` in the semantic composition digest. Changing only a target label therefore invalidates semantic provenance even before musical verification considers whether the altered label matches the notes.

Historical payloads without tonicization metadata remain loadable when their specification has tonicization disabled. A tonicization-enabled v2.6 artifact without explicit target metadata fails closed under `CM037`.

## Scope boundary

v2.6 does not implement modal mixture, secondary leading-tone chords, persistent local-key regions, arbitrary chromatic sonorities, pivot-chord analysis, modulation, or third-inversion sevenths. Those features require additional explicit representation and verifier semantics rather than broadening the current target field beyond what it certifies.
