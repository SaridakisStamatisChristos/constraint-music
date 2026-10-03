# Modal Mixture

Constraint Music v2.7 adds **verified modal mixture** as an opt-in harmonic-context dimension. The release deliberately supports a narrow, explicit form of mixture: borrowed **triads** from one canonical parallel source mode.

The goal is not to make every chromatic pitch globally legal. The goal is to make borrowed harmony typed, reconstructable, independently verifiable, and backward compatible with the existing tonal/SATB contract.

## Enabling modal mixture

```yaml
modal_mixture_enabled: true
minimum_borrowed_chords: 1
```

Modal mixture is independent of `harmony_vocabulary`. Borrowed triads therefore work with the default `triads` vocabulary and can also coexist in a piece that enables diatonic sevenths or v2.6 tonicization. A single beat cannot be both borrowed and tonicized.

## Canonical source modes

v2.7 admits exactly one parallel source for each global mode:

- global major -> **parallel natural minor**;
- global minor -> **parallel major**.

The existing global minor model remains harmonic minor. Borrowing from *parallel natural minor* is therefore a distinct, explicit source-mode operation rather than a silent mutation of the global scale.

Each beat carries nullable `modal_sources` metadata. `null` means ordinary global-key harmony. A borrowed beat stores either `parallel_natural_minor` or `parallel_major`, as determined by the global mode.

## Harmonic identity

A borrowed sonority is not stored as a Roman-numeral string. Its canonical identity remains decomposed:

1. global functional `chord_degree`;
2. `ChordKind` (v2.7 borrowed forms are triads only);
3. inversion;
4. nullable tonicization target;
5. nullable modal source;
6. realized SATB pitches.

Roman/source notation is derived presentation. In C major, degree 4 borrowed from the parallel natural minor is reconstructed as `iv[parallel_natural_minor]` (with `6` or `64` appended for first/second inversion).

## Source-derived realization

For a borrowed beat, the theory layer derives the seven pitch classes of the explicit source mode, then constructs the source-mode triad on the stored degree. The SATB relation table admits only realizations containing the complete borrowed triad.

For example, in C major:

- global degree IV = F-A-C;
- parallel-natural-minor degree iv = F-Ab-C;
- the borrowed triad is therefore F-Ab-C.

The altered Ab is not granted global pitch-domain status. It exists because the beat explicitly carries the parallel-natural-minor source identity.

## Preserved outer-voice contract

v2.7 does **not** reinterpret `CM005` or `CM006`.

- Strong melody/soprano remains a member of the global triadic core identified by `chord_degree`.
- Bass remains a member of that same global triadic core.

Borrowed chromatic tones are therefore carried by alto/tenor. The theory layer exposes only borrowed degrees whose source triad shares enough pitch-class structure to remain representable under this historical outer-voice boundary.

This is a compatibility decision, not a music-theory claim that other borrowed chords are invalid.

## Global cadence boundary

Borrowing is forbidden on the final beat. When `require_authentic_cadence` is enabled, the penultimate beat is also forced to remain in the global context. The established whole-piece cadence therefore keeps exactly its previous meaning.

`minimum_borrowed_chords` is validated against the number of beats available outside that preserved cadential boundary, so impossible declarations fail before CP-SAT construction.

## Independent verification

v2.7 extends the hard-rule contract to 42 IDs:

- **CM041 — modal mixture context**: source metadata shape, feature enablement, canonical source identity, supported degree, triadic form, no tonicization overlap, global cadence boundary, and minimum borrowed-chord count.
- **CM042 — borrowed chord realization**: source-derived triad completeness and inversion/bass agreement.

The verifier reconstructs borrowed pitch classes from the serialized global key, degree, and modal source. It does not trust the display name or CP-SAT table membership.

## Search semantics

`modal_source` is a new independent no-good dimension:

```bash
constraint-music generate examples/modal_mixture.yaml \
  --count 2 \
  --distinct-on modal_source \
  --output build/mixture.mid \
  --json build/mixture.json
```

Existing meanings remain unchanged:

- `harmony` = global chord-degree sequence;
- `harmonic_form` = chord kind + inversion;
- `tonicization` = nullable local-target sequence;
- `modal_source` = nullable source-mode sequence;
- `voicing` = alto/tenor realization.

Two outputs can therefore share the same global functional progression while differing only in whether a compatible beat is realized as global or borrowed harmony.

## Provenance and compatibility

Artifact schema 2.7 commits `modal_sources` into the semantic composition digest. Changing a borrowed-source declaration without recomputing provenance is detected even when all note arrays are left untouched.

Older artifacts do not receive invented modal-source metadata. Missing source metadata remains acceptable when the loaded specification has modal mixture disabled; a current modal-mixture-enabled artifact must serialize the source sequence explicitly.

## Deliberate v2.7 exclusions

v2.7 does not claim to implement:

- borrowed seventh chords;
- secondary leading-tone chords;
- arbitrary altered chords;
- persistent local-key regions;
- pivot-chord analysis or modulation;
- third-inversion sevenths.

Borrowed sevenths are intentionally deferred because they require source-aware seventh and tendency-tone semantics rather than silently reusing the global CM035/CM036 rules.
