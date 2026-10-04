# Applied-Dominant Tonicization

Constraint Music v2.6 introduced a bounded, independently verifiable tonicization model based on applied dominant sevenths. The v2.10 contract preserves that model and now shares the existing local-target identity field with a second, form-distinguished chromatic function: secondary leading-tone triads.

## Design goal

The original release introduced local dominant function without pretending that a one-chord tonicization is a permanent key change and without granting unrestricted chromatic pitch access.

Global artifact key, active local key, functional chord degree, chord kind, inversion, local target, modal source, and SATB voicing remain separate data.

## Configuration

Applied-dominant tonicization remains opt-in and requires the v2.5 seventh-chord vocabulary:

```yaml
harmony_vocabulary: triads+sevenths
tonicization_enabled: true
minimum_applied_dominants: 1
```

Under the current v2.10 contract, `minimum_applied_dominants` counts beats carrying both a non-null local target **and** `ChordKind.SEVENTH`. A v2.10 target-bearing triad is a secondary leading-tone chord and cannot counterfeit the applied-dominant minimum.

An applied dominant cannot occupy the final beat because immediate target resolution is part of the hard contract.

## Semantic representation

Ordinary harmony has:

```text
chord_degree = d
chord_kind = triad | seventh
inversion = 0 | 1 | 2
tonicization_target = null
```

An applied dominant has:

```text
chord_degree = active-key diatonic support/root degree of the applied dominant
chord_kind = seventh
inversion = 0 | 1 | 2
tonicization_target = target scale degree
```

From v2.10 onward, the same target field can also participate in:

```text
chord_kind = triad
tonicization_target = target scale degree
```

That pairing is **not** an applied dominant; it is governed by CM052–CM054 as a secondary leading-tone chord. Roman/slash strings remain derived presentation, never canonical solver state.

## Pitch construction

For applied-dominant target scale degree `t` in exact active key `K`:

1. resolve the target pitch class from `K`;
2. place the applied-dominant root a perfect fifth above that target;
3. construct a dominant seventh above the root with intervals `0, 4, 7, 10` semitones;
4. require the SATB realization to contain those four pitch classes exactly once.

In C major, target degree 5 is G. Its applied dominant is D7 with pitch classes D-F#-A-C, displayed as `V7/V` in root position.

When persistent modulation is enabled, `K` means the exact active local key at that beat. Post-boundary tonicization is therefore derived from the destination key rather than stale global-key context.

## Target support and backward compatibility

`CM005` and `CM006` predate chromatic harmony and retain their established meanings: strong melody/soprano and bass must belong to the active-key diatonic triadic core identified by the beat's stored degree.

The applied-dominant model does not redefine those rules. Instead, the tonal layer computes a supported-target set for which a complete applied dominant can be realized while soprano and bass remain compatible with that established triadic-core contract. Chromatic applied tones are carried by inner voices where required.

This means the set of exposed targets depends on key/mode and the preserved representation contract. A missing target is a compatibility limitation of the certified model, not a music-theory claim that the tonicization is invalid.

v2.10 secondary leading-tone chords use their own deterministic support-degree policy rather than pretending the chromatic diminished root is a diatonic degree. See [Secondary Leading-Tone Chords](SECONDARY_LEADING_TONE.md).

## Resolution contract

Every applied dominant must resolve on the immediately following beat:

```text
beat n:     chord_kind = seventh
            tonicization_target = t
beat n + 1: chord_degree = t
            tonicization_target = null
```

The applied chordal seventh resolves downward by step: `-1` or `-2` semitones.

The applied dominant's major third functions as the local leading tone and resolves upward by exactly one semitone. Both rules are checked in whichever SATB voice carries the tendency tone.

## Hard-rule IDs

v2.6 added:

- `CM037` — applied-dominant target context, eligibility, and minimum-count semantics;
- `CM038` — target-derived applied-dominant realization and inversion consistency;
- `CM039` — immediate resolution to the declared untargeted local tonic;
- `CM040` — applied seventh and local-leading-tone resolution.

In contract 2.10, CM037/CM038 explicitly apply to **target-bearing seventh forms**. Target-bearing triads route to CM052–CM054. This is a versioned semantic clarification, not a silent widening of applied-dominant identity.

The solver compiles these requirements and the independent verifier reconstructs them from serialized notes and metadata.

## Distinct enumeration

`tonicization` remains a separate no-good dimension:

```bash
constraint-music generate examples/applied_dominants.yaml \
  --count 3 \
  --distinct-on tonicization,voicing \
  --output build/variant.mid \
  --json build/variant.json
```

This preserves the meanings of:

- `harmony`: stored functional/support degree sequence;
- `harmonic_form`: chord kind + inversion;
- `tonicization`: nullable local target sequence;
- `modal_source`: nullable parallel-source sequence;
- `key_context`: persistent active-key sequence;
- `voicing`: alto + tenor pitches.

Target identity and harmonic form therefore remain orthogonal even though their combination selects the certified local chromatic function.

## Provenance

Current artifact schema/contract 2.10 commits `tonicization_targets` together with harmonic-form and active-key context metadata when present. Changing only a target therefore invalidates semantic provenance even before musical verification decides whether the altered target matches the notes.

Historical payloads without target metadata remain loadable when their specification requires neither tonicization nor secondary leading-tone harmony. An enabled feature without the semantic data needed for its independent reconstruction fails closed under its corresponding contract rules.

## Scope boundary

Applied dominants and secondary leading-tone triads are local target events, not persistent key changes. Persistent local-key regions remain the v2.8 modulation subsystem.

The current contract does not certify secondary leading-tone seventh chords, arbitrary chromatic sonorities, arbitrary modulation chains, third-inversion sevenths, enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, or probabilistic key inference. Those require explicit future representation and verifier semantics rather than weakening the existing target model.
