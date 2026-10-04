# Borrowed Seventh Chords — v2.9

Constraint Music v2.9 extends verified modal mixture to a deliberately narrow subset of source-derived seventh chords. The feature is not a general chromatic-harmony switch and does not infer key centers.

## Enable

Borrowed sevenths arise only when modal mixture and the existing seventh vocabulary are both enabled:

```yaml
harmony_vocabulary: triads+sevenths
modal_mixture_enabled: true
minimum_borrowed_chords: 1
minimum_seventh_chords: 1
```

No new opaque chord field is added. A borrowed seventh is identified by the existing semantic axes:

- active local key;
- functional chord degree;
- `ChordKind.SEVENTH`;
- inversion;
- explicit non-null modal source;
- SATB realization.

## Canonical source

The source is determined from the exact active local key at the beat:

- active major -> parallel natural minor;
- active minor -> parallel major.

After a v2.8 modulation, this means the destination key supplies the tonic and mode for source derivation. The original global key remains immutable metadata but is not reused as stale borrowing context.

## Pitch construction

For functional degree `d`, the theory layer builds scale degrees `d`, `d+2`, `d+4`, and `d+6` in the canonical parallel source. These four pitch classes are the complete expected borrowed seventh.

The verifier independently performs the same derivation from serialized values. It does not trust a solver row, a display label, or the fact that CP-SAT generated the artifact.

## Narrow eligibility filter

v2.9 intentionally does not certify every source-mode seventh. An admitted borrowed seventh must satisfy all of the following:

1. it differs from the active-key seventh on the same functional degree;
2. its complete source-derived four-tone set remains compatible with the historical CM005/CM006 outer-voice triadic core;
3. at least two distinct source-chord tones are available to that active-key triadic core so soprano and bass can remain distinct SATB outer voices;
4. its source-derived chordal seventh equals the already-certified active-key chordal-seventh pitch class, preserving solver/verifier symmetry for downward seventh resolution;
5. when the canonical source is parallel major, the source leading tone is not simultaneously treated as the chordal seventh.

Under the current major/harmonic-minor theory model this yields a small deterministic whitelist rather than unrestricted source-mode seventh permission.

## Realization

CM050 requires:

- all four expected source-derived pitch classes;
- each expected pitch class exactly once;
- no missing member replaced by a duplicate;
- inversion in `0..2` only;
- realized bass pitch class equal to the chord member selected by the serialized inversion.

Third-inversion sevenths remain outside v2.9 because supporting them would require an explicit outer-voice compatibility revision.

## Context exclusions

CM049 rejects a borrowed seventh when:

- the source is not canonical for the active key;
- the degree is outside the certified whitelist;
- a tonicization target is present on the same beat;
- the beat is a certified modulation pivot/context anchor;
- the beat belongs to the certified terminal destination cadence;
- the final chord would otherwise have no following resolution.

Modal mixture remains explicit and opt-in. A non-null source never grants arbitrary chromatic pitch permission.

## Tendency-tone resolution

CM051 adds source-aware motion semantics:

- every SATB voice carrying the borrowed chordal seventh resolves downward by one or two semitones on the following sonority;
- when the canonical source is parallel major, any SATB voice carrying an admitted source leading tone resolves upward by one semitone.

These checks are compiled into CP-SAT and independently reconstructed after solving.

## Interaction with v2.8 modulation

The v2.8.0a2 strict modulation model is unchanged:

- storage may use the union of declared persistent key regions;
- each concrete melody/bass step is gated by its exact active key;
- the terminal CM032 path is not skipped;
- CM047 still requires destination-leading-tone presence and upward resolution in every carrier.

Borrowed sevenths are excluded from the pivot and terminal destination V-I, so v2.9 cannot weaken the certified modulation closure.

## Search and provenance

No search axis is redefined:

- `harmonic_form` records seventh/inversion identity;
- `modal_source` records borrowed-source identity;
- `key_context` records persistent active-key identity.

Artifact schema `2.9` already commits all three semantic dimensions through the existing harmonic-form, modal-source, and key-context fields. Tampering with a source declaration or harmonic form therefore changes the semantic composition digest.

## New hard rules

- **CM049 — borrowed-seventh context/eligibility**
- **CM050 — source-derived borrowed-seventh realization/inversion**
- **CM051 — borrowed-seventh/source tendency resolution**

The pre-existing CM041/CM042 borrowed-triad meaning remains intact; v2.9 routes eligible seventh forms into the additive CM049–CM051 family instead of silently redefining triad realization.

## Deliberately deferred

v2.9 does not add:

- secondary leading-tone chords;
- third-inversion sevenths;
- arbitrary modulation chains;
- distant-key or enharmonic reinterpretation;
- augmented-sixth or Neapolitan reinterpretation;
- probabilistic/free key-center inference.
