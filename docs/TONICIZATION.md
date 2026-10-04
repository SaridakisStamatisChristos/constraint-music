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

## v2.11 classification boundary

In v2.10, target-bearing triads were separated from applied dominants by harmonic form. v2.11 adds a second target-bearing **seventh** family, so form alone is no longer sufficient to classify every target-bearing seventh.

`minimum_applied_dominants` now counts only beats whose serialized musical values reconstruct exactly as active-key `V7/x`:

1. non-null supported local target;
2. `ChordKind.SEVENTH`;
3. correct active-key applied-dominant root/support degree;
4. exact target-derived dominant-seventh pitch set;
5. four distinct chord tones;
6. supported inversion whose bass agrees with the reconstructed chord.

A v2.11 fully diminished `vii°7/x` therefore cannot counterfeit the applied-dominant minimum merely because it carries a target and seventh form.

The verifier independently reconstructs this distinction; no serialized `function_type` flag is trusted.

## Semantic representation

Ordinary harmony:

```text
chord_degree = d
chord_kind = triad | seventh
inversion = 0 | 1 | 2
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

The same target field also participates in two separate secondary leading-tone families:

```text
target + triad + exact diminished-triad identity
    -> CM052-CM054

target + seventh + exact fully diminished identity
    -> CM055-CM057
```

Roman/slash strings remain derived presentation, never canonical solver state.

## Pitch construction

For applied-dominant target scale degree `t` in exact active key `K`:

1. resolve the target pitch class from `K`;
2. place the applied-dominant root a perfect fifth above that target;
3. construct a dominant seventh with intervals `0, 4, 7, 10` semitones;
4. require the SATB realization to contain those four pitch classes exactly once.

In C major, target degree 5 is G. Its applied dominant is D7: D-F#-A-C, displayed as `V7/V` in root position.

When persistent modulation is enabled, `K` is the exact active local key at that beat. Post-boundary tonicization is derived from the destination key, never stale global-key context.

## Target support and backward compatibility

CM005 and CM006 predate chromatic harmony and retain their established meanings: strong melody/soprano and bass must belong to the active-key diatonic triadic core identified by the stored degree.

The applied-dominant model therefore exposes only targets representable under that outer-voice contract. A missing target is a certified-representation limitation, not a general music-theory claim.

Secondary leading-tone triads and sevenths use their own deterministic support-degree policy rather than pretending a chromatic diminished root is an ordinary diatonic degree. See [Secondary Leading-Tone Triads](SECONDARY_LEADING_TONE.md) and [Secondary Leading-Tone Seventh Chords](SECONDARY_LEADING_TONE_SEVENTHS.md).

## Resolution contract

Every applied dominant resolves on the immediately following beat:

```text
beat n:     exact applied V7/x
beat n + 1: chord_degree = x
            tonicization_target = null
```

The applied chordal seventh resolves downward by one or two semitones. The applied dominant's major third is the local leading tone and resolves upward by exactly one semitone. The solver constrains these tendencies and the verifier checks whichever SATB voice carries them.

## Hard-rule IDs

- `CM037` — exact applied-dominant context, identity, and minimum-count semantics;
- `CM038` — target-derived applied-dominant realization and inversion consistency;
- `CM039` — immediate resolution to the declared untargeted local tonic;
- `CM040` — applied chordal-seventh and local-leading-tone resolution.

v2.11 narrows CM037/CM038 classification to exact `V7/x` identity rather than silently weakening those rules to absorb secondary leading-tone sevenths.

## Distinct enumeration

`tonicization` remains a separate no-good dimension. This preserves the meanings of `harmony`, `harmonic_form`, `tonicization`, `modal_source`, `key_context`, and `voicing` as independent axes even when combinations of those axes reconstruct a particular chromatic function.

## Provenance

Artifact schema/contract `2.11` commits local targets together with harmonic form, voicing, modal source, key context, and the generation specification. Changing only a target can therefore invalidate semantic provenance even before musical verification determines whether altered metadata matches the notes.

Historical payloads without target metadata remain loadable only when their specification does not require a feature that depends on target reconstruction.

## Scope boundary

Applied dominants, secondary leading-tone triads, and secondary leading-tone sevenths are local target events, not persistent key changes. Persistent local-key regions remain the v2.8 modulation subsystem.

v2.11 still does not certify arbitrary chromatic sonorities, half-diminished secondary leading-tone sevenths, third-inversion seventh handling, arbitrary modulation chains, distant/enharmonic modulation, augmented-sixth/Neapolitan reinterpretation, or probabilistic key inference.
