# Architecture

Constraint Music is a deterministic symbolic-composition system built around a strict separation between **proposal/solve** and **independent certification**.

## Core pipeline

```text
GenerationSpec / YAML
        |
        v
configuration validation
        |
        v
CP-SAT compiler
  tonal + rhythm + phrase
  SATB + harmonic identity
  local target / modal source
  persistent active key
        |
        v
OR-Tools solve
        |
        v
ordinary result values
        |
        +--> independent CM001-CM057 verifier
        +--> independent objective recomputation
        +--> provenance / artifact digests
        |
        v
verified JSON + MIDI
```

A feasible solver assignment is never equivalent to a verified composition. Export occurs only after the application-level verifier reconstructs the declared semantics from serialized musical values.

## Orthogonal semantic axes

The architecture avoids a monolithic Roman-numeral or chord-label state. Harmonic meaning is decomposed into independent axes:

- functional/support degree;
- harmonic kind (`TRIAD` / `SEVENTH`);
- inversion;
- nullable local target identity;
- nullable modal-source identity;
- persistent active-key context;
- SATB realization.

This decomposition is the compatibility mechanism across the v2 line. New harmonic families are admitted by narrowly versioned reconstruction rules rather than by replacing old axes or trusting opaque labels.

## Global key vs. active local key

The artifact-global key remains immutable. v2.8 introduced explicit persistent active-key contexts for one certified same-mode modulation to the dominant key.

Before the declared boundary, the active key is the source key. From the boundary onward, the active key is the destination key. Theory, pitch admission, harmonic reconstruction, local-target functions, modal borrowing, and objective tension use the exact active key at the beat.

The solver may use a union storage domain to hold source- and destination-key pitches, but every musical use is gated by the exact local context. The verifier independently enforces the same distinction.

## Outer-voice compatibility and the v2.12 exception

CM005 and CM006 historically bind strong melody/soprano and bass to the active-key triadic core represented by the stored degree. Most later chromatic features preserve that contract through a deterministic **support degree**.

A complete third-inversion secondary leading-tone seventh cannot preserve the old bass shortcut: by definition, its chordal seventh is in the bass and may be chromatic to the active key. v2.12 therefore introduces a deliberately scoped exception rather than weakening the global contract:

- the expanded melody/bass storage domain is selected only when `secondary_leading_tone_seventh_enabled` is true;
- ordinary beats still require the established diatonic/support interpretation;
- a chromatic strong soprano or bass receives the exception only after the beat independently reconstructs as an exact secondary leading-tone seventh;
- malformed target-bearing chords receive no broad chromatic permission;
- inversion `3` is legal only for an independently reconstructed secondary leading-tone seventh; other forms retain the established inversion range.

The support degree still carries progression-graph compatibility. Target identity + active key + SATB realization carry the actual chromatic function.

## Harmonic-family routing

### Diatonic triads and sevenths

The v2.5 harmonic-form layer supports diatonic triads and complete seventh chords under its established outer-voice/inversion contract.

### Applied dominants

v2.6 adds explicit nullable target identity. An applied dominant is reconstructed as exact active-key `V7/x` pitch/support identity and immediate target resolution.

### Modal mixture and borrowed sevenths

v2.7 adds explicit canonical parallel-source identity. v2.9 composes source identity with seventh form and active-key context for a deliberately filtered borrowed-seventh subset.

### Secondary leading-tone triads

v2.10 reuses target identity for `vii°/x` triads. The chromatic diminished root is never stored as a fake diatonic degree; a support-degree bridge preserves progression semantics.

### Complete secondary leading-tone sevenths

v2.12 supersedes v2.11's deliberately narrow secondary-seventh subset. No new trusted serialized function or quality axis is introduced.

A target-bearing seventh is classified from exact active-key musical identity:

```text
exact active-key V7/x support + pitch set + inversion
    -> applied dominant

exact target-derived fully diminished pitch set + support + inversion
    -> vii°7/x family

exact target-derived eligible half-diminished pitch set + support + inversion
    -> viiø7/x family
```

For a major local target, both fully diminished and half-diminished qualities are eligible. For a minor local target, the certified quality is fully diminished. Diminished and augmented targets are not local-tonic targets in this subsystem.

All four inversion figures are supported for the certified family: `7`, `65`, `43`, and `42`.

## Exact tendency semantics

The v2.12 compiler and independent verifier agree on exact target- and quality-dependent resolution deltas:

- local leading tone/root: `+1` semitone;
- diminished fifth: `-1` for a major target, `-2` for a minor target;
- fully diminished chordal seventh: `-1` semitone;
- half-diminished chordal seventh: `-2` semitones.

The rule is voice-agnostic and therefore applies to the bass in a genuine third inversion.

## Solver witnesses are not artifact identity

The compiler may derive internal Boolean/quality witnesses to count exact applied dominants, secondary-leading-tone triads, and secondary-leading-tone sevenths. Those values are solver implementation details only.

They are not the verifier's source of truth. The verifier independently re-derives classification from ordinary result values: active key, target, support degree, chord kind, inversion, modal-source absence, and SATB pitches.

This preserves the decomposed artifact model and prevents a forged label from certifying a chord.

## Protected anchors

The v2.8.0a2 modulation repair remains a protected architecture boundary. Certified chromatic functions cannot contaminate anchors where that would undermine:

- source-I/destination-IV pivot identity;
- destination V-I confirmation;
- exact destination-leading-tone presence;
- upward destination-leading-tone resolution;
- persistent active-key interpretation.

Secondary leading-tone triads and sevenths remain excluded from those protected positions.

## Verification routing

The independent verifier routes from the declared feature set while preserving earlier contracts:

- ordinary SATB verification;
- modulation-aware SATB verification;
- borrowed-seventh verification when source-aware sevenths are enabled;
- secondary-leading-tone-triad verification for the v2.10 feature;
- complete secondary-leading-tone-seventh verification for the v2.12 feature.

The v2.12 verifier first separates exact applied-dominant beats, then independently reconstructs secondary-seventh quality and inversion. It also performs a second inversion-scope guard so `3` cannot leak onto a non-secondary chord merely because the feature is enabled.

## Provenance

Artifact schema and constraint-contract version are both `2.12`.

Semantic provenance commits:

- the full generation specification;
- melody, rhythm, bass, and chord/support degrees;
- SATB voices;
- harmonic kind and inversion;
- local target metadata;
- modal-source metadata;
- persistent key contexts;
- objective-vector metadata.

Because secondary-seventh quality/function identity is reconstructed from those values, no synthetic trusted quality/function field is required.

## Search and optimization remain separate

No-good distinctness and objective scalarization do not define musical validity. The verifier checks the hard contract independently of how a candidate was discovered or ranked.

Distinctness dimensions remain orthogonal: melody, rhythm, bass, harmony, voicing, harmonic form, tonicization target, modal source, and key context.

## Version boundaries

Current package: `2.12.0a1`

Current artifact schema: `2.12`

Current constraint contract: `2.12`

Current hard-rule range: `CM001-CM057`

v2.12 completes the secondary leading-tone seventh family claimed by this subsystem. Separate future domains include arbitrary modulation chains, distant/enharmonic modulation, broad enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, unrestricted chromatic-function inference, and probabilistic key/function inference.
