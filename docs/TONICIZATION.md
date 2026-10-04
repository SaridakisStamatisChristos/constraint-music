# Applied-Dominant Tonicization

Constraint Music v2.6 introduced a bounded, independently verifiable tonicization model based on applied dominant sevenths. Later releases reused the same nullable local-target identity for other certified target-bearing functions without turning it into an opaque chord-name field.

## Design goal

A one-chord tonicization is not a persistent key change and does not grant unrestricted chromatic pitch access.

Global artifact key, active local key, functional/support degree, chord kind, inversion, local target, modal source, and SATB voicing remain separate data.

## Configuration

Applied-dominant tonicization remains opt-in and requires the seventh-chord vocabulary:

```yaml
harmony_vocabulary: triads+sevenths
tonicization_enabled: true
minimum_applied_dominants: 1
```

An applied dominant cannot occupy the final beat because immediate target resolution is part of the hard contract.

## Exact classification boundary

Since v2.11, target-bearing seventh form alone is insufficient to classify function. v2.12 completes the second target-bearing seventh family, so the verifier now separates three exact cases rather than trusting a generic target flag:

```text
target + triad + exact diminished-triad identity
    -> secondary leading-tone triad (CM052-CM054)

target + seventh + exact active-key V7/x identity
    -> applied dominant (CM037-CM040)

target + seventh + exact eligible vii°7/x or viiø7/x identity
    -> secondary leading-tone seventh (CM055-CM057)
```

`minimum_applied_dominants` counts only beats whose serialized musical values reconstruct exactly as active-key `V7/x`:

1. non-null supported local target;
2. `ChordKind.SEVENTH`;
3. correct active-key applied-dominant root/support identity;
4. exact target-derived dominant-seventh pitch set;
5. four distinct chord tones;
6. supported applied-dominant inversion whose bass agrees with the reconstructed chord.

A fully diminished or eligible half-diminished secondary leading-tone seventh therefore cannot counterfeit the applied-dominant minimum merely because it carries a target and seventh form.

No serialized `function_type` or trusted quality label is required.

## Semantic representation

Ordinary harmony:

```text
chord_degree = d
chord_kind = triad | seventh
inversion = family-supported value
tonicization_target = null
```

A certified applied dominant:

```text
chord_degree = active-key applied-dominant root/support degree
chord_kind = seventh
inversion = 0 | 1 | 2
tonicization_target = target scale degree
SATB pitch set = exact active-key V7/x
```

A certified v2.12 secondary leading-tone seventh uses the same target field but is reconstructed from its target-derived diminished sonority and may use inversion `0 | 1 | 2 | 3` under CM055-CM057.

Roman/slash strings remain derived presentation, never canonical solver state.

## Pitch construction

For applied-dominant target scale degree `t` in exact active key `K`:

1. resolve the target pitch class from `K`;
2. place the applied-dominant root a perfect fifth above that target;
3. construct a dominant seventh with intervals `0, 4, 7, 10` semitones;
4. require the SATB realization to contain those four pitch classes exactly once.

In C major, target degree 5 is G. Its applied dominant is D7: D-F#-A-C, displayed as `V7/V` in root position.

When persistent modulation is enabled, `K` is the exact active local key at that beat. Post-boundary tonicization is derived from the destination key, never stale global-key context.

## Support and compatibility boundaries

Applied dominants continue to use the established support/outer-voice policy certified by CM037-CM040. v2.12 does **not** broaden applied-dominant inversions merely because secondary leading-tone sevenths gained genuine `42` support.

Secondary leading-tone triads and sevenths use their deterministic support-degree bridge rather than pretending a chromatic diminished root is an ordinary diatonic degree. For the secondary-seventh path only, v2.12 scopes the chromatic outer-voice exception required to certify an actual seventh-in-bass `42`; ordinary and applied-dominant beats do not inherit that exception.

See [Secondary Leading-Tone Triads](SECONDARY_LEADING_TONE.md) and [Secondary Leading-Tone Seventh Chords](SECONDARY_LEADING_TONE_SEVENTHS.md).

## Applied-dominant resolution contract

Every applied dominant resolves on the immediately following beat:

```text
beat n:     exact applied V7/x
beat n + 1: chord_degree = x
            tonicization_target = null
```

The applied chordal seventh resolves downward by one or two semitones. The applied dominant's major third is the local leading tone and resolves upward by exactly one semitone. The solver constrains these tendencies and the verifier checks whichever SATB voice carries them.

Secondary leading-tone sevenths use their own exact target-/quality-dependent CM057 tendency semantics.

## Hard-rule IDs

- `CM037` — exact applied-dominant context, identity, and minimum-count semantics;
- `CM038` — target-derived applied-dominant realization and inversion consistency;
- `CM039` — immediate resolution to the declared untargeted local tonic;
- `CM040` — applied chordal-seventh and local-leading-tone resolution.

CM037/CM038 classify only exact `V7/x` identity; they are not weakened to absorb other target-bearing seventh functions.

## Distinct enumeration

`tonicization` remains a separate no-good dimension. This preserves the meanings of `harmony`, `harmonic_form`, `tonicization`, `modal_source`, `key_context`, and `voicing` as independent axes even when combinations of those axes reconstruct a particular chromatic function.

## Provenance

Artifact schema/contract `2.12` commits local targets together with harmonic form, voicing, modal source, key context, and the generation specification. Changing only a target can therefore invalidate semantic provenance even before musical verification determines whether altered metadata matches the notes.

Historical payloads without target metadata remain loadable only when their specification does not require a feature that depends on target reconstruction.

## Scope boundary

Applied dominants, secondary leading-tone triads, and secondary leading-tone sevenths are local target events, not persistent key changes. Persistent local-key regions remain the v2.8 modulation subsystem.

v2.12 completes the secondary leading-tone seventh family claimed by CM055-CM057. Arbitrary modulation chains, distant/enharmonic modulation, augmented-sixth/Neapolitan reinterpretation, unrestricted chromatic-function inference, and probabilistic key inference remain separate domains.
