# Modal Mixture

Constraint Music introduced verified modal mixture in v2.7 as an opt-in harmonic-context dimension. The core model remains explicit: each borrowed beat carries a canonical parallel-source identity, and chromatic pitch content is derived from that source rather than globally permitted.

v2.7 certified borrowed triads. v2.9 adds a narrow, separately verified borrowed-seventh extension when the existing seventh vocabulary is also enabled.

## Enable

Borrowed triads:

```yaml
modal_mixture_enabled: true
minimum_borrowed_chords: 1
```

Borrowed sevenths additionally require:

```yaml
harmony_vocabulary: triads+sevenths
minimum_seventh_chords: 1
```

A beat cannot be both borrowed and tonicized.

## Canonical source modes

The source is selected from the **exact active local key** at the beat:

- active major -> parallel natural minor;
- active minor -> parallel major.

The repository's minor-key tonal model remains harmonic minor. Parallel natural minor is therefore a distinct source operation rather than a silent mutation of the active scale.

Each beat carries nullable `modal_sources` metadata. `null` means ordinary active-key harmony. A borrowed beat stores `parallel_natural_minor` or `parallel_major` as determined by active mode.

Before v2.8, active key and global key were identical. After a certified v2.8 modulation, source derivation uses the persistent destination active key, never stale global-key context.

## Harmonic identity

Borrowed harmony is not stored as an opaque Roman-numeral string. Identity remains decomposed into:

1. immutable artifact/global key;
2. active local key;
3. functional `chord_degree`;
4. `ChordKind`;
5. inversion;
6. nullable tonicization target;
7. nullable modal source;
8. SATB realization.

Roman/source notation is derived presentation only.

## Borrowed triads

For a source-bearing triad, the theory layer derives the seven pitch classes of the explicit source mode and constructs the source triad on the stored degree. CM042 independently requires complete source-derived triadic realization and inversion/bass agreement.

CM005 and CM006 retain their established active-key triadic-core meaning. Chromatic borrowed tones are therefore carried where necessary by inner voices. Only source degrees representable under that compatibility boundary are exposed.

## Borrowed sevenths in v2.9

When expanded harmony is enabled, a source-bearing seventh is routed to additive rules CM049–CM051 rather than being treated as a v2.7 triad.

v2.9 admits only a structural whitelist that preserves CM005/CM006 and established seventh-resolution semantics. Complete four-tone source derivation, inversion/bass agreement, chordal-seventh motion, and any admitted parallel-major source leading tone are independently verified.

See [Borrowed Seventh Chords](BORROWED_SEVENTHS.md) for the exact eligibility filter and tendency-tone contract.

## Certified anchor exclusions

Borrowing remains excluded from certified cadence/context anchors. Under v2.8 modulation, this includes the common-chord pivot and terminal destination V-I. v2.9 borrowed sevenths cannot weaken the strict v2.8.0a2 terminal leading-tone contract.

## Search semantics

`modal_source` remains an independent no-good dimension. Other meanings are unchanged:

- `harmony` = functional degree sequence;
- `harmonic_form` = chord kind + inversion;
- `tonicization` = nullable local-target sequence;
- `modal_source` = nullable source-mode sequence;
- `key_context` = persistent active-key sequence;
- `voicing` = SATB realization.

## Provenance and compatibility

Current schema 2.9 commits modal-source identity together with harmonic form and key contexts when present. Changing a source declaration without recomputing provenance is detectable even when note arrays remain untouched.

Older artifacts do not receive invented modal-source or key-context metadata. Existing v2.7/v2.8 borrowed-triad semantics remain loadable and unchanged when newer seventh behavior is not present.

## Deliberate exclusions

Current modal-mixture support does not imply:

- secondary leading-tone chords;
- arbitrary altered chords;
- third-inversion sevenths;
- arbitrary modulation chains;
- distant-key/enharmonic reinterpretation;
- augmented-sixth or Neapolitan reinterpretation;
- probabilistic/free key-center inference.
