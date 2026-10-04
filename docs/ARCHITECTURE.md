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

This decomposition is the main compatibility mechanism across v2.5-v2.11. New harmonic families are admitted by adding narrowly versioned reconstruction rules instead of replacing older axes.

## Global key vs. active local key

The artifact-global key remains immutable. v2.8 introduced explicit persistent active-key contexts for one certified same-mode modulation to the dominant key.

Before the declared boundary, the active key is the source key. From the boundary onward, the active key is the destination key. Theory, pitch admission, harmonic reconstruction, local-target functions, modal borrowing, and objective tension all use the exact active key at the beat.

The solver may use a union storage domain to hold source- and destination-key pitches, but every musical use is gated by the exact local context. The verifier independently enforces the same distinction.

## Preserved outer-voice contract

CM005 and CM006 historically bind the strong melody/soprano and bass to the active-key triadic core represented by the stored degree. Later chromatic features preserve that contract rather than silently redefining it.

For chromatic secondary leading-tone families, the stored degree is therefore a deterministic **support degree**. The actual chromatic sonority is reconstructed from active key + target identity + harmonic form + voicing.

This lets CM005/CM006/CM007 keep their historical meaning while the inner harmonic function can be chromatic.

## Harmonic-family routing

### Diatonic triads and sevenths

The v2.5 harmonic-form layer supports diatonic triads and complete seventh chords, with root/first/second inversion under the preserved outer-voice contract.

### Applied dominants

v2.6 adds explicit nullable target identity. An applied dominant is reconstructed as exact active-key `V7/x` pitch/support identity and immediate target resolution.

### Modal mixture and borrowed sevenths

v2.7 adds explicit canonical parallel-source identity. v2.9 composes source identity with seventh form and active-key context for a narrow verified borrowed-seventh subset.

### Secondary leading-tone triads

v2.10 reuses target identity for `vii°/x` triads. The chromatic diminished root is never stored as a fake diatonic degree; a support-degree bridge preserves historical outer-voice/progression semantics.

### Secondary leading-tone sevenths

v2.11 adds a separate opt-in fully diminished seventh family. It does not introduce a new serialized function axis.

A target-bearing seventh is classified from exact active-key musical identity:

```text
exact active-key V7/x support + pitch set + inversion
    -> applied dominant

exact active-key fully diminished vii°7/x support + pitch set + inversion
    -> secondary leading-tone seventh
```

The two families therefore share target and seventh-form axes but remain disjoint by reconstructed pitch/support identity.

## v2.11 quality boundary

The certified v2.11 secondary-leading-tone-seventh family supports:

- fully diminished quality only;
- root, first, and second inversion only;
- all four target-derived pitch classes exactly once;
- immediate resolution to the declared untargeted, unborrowed triadic target;
- local leading tone up by semitone;
- diminished fifth down by step;
- chordal diminished seventh down by step.

Half-diminished quality and third inversion remain outside the contract.

## Solver-side identity flags are not artifact identity

The v2.11 compiler may derive internal Boolean flags to count exact applied dominants, secondary-leading-tone triads, and secondary-leading-tone sevenths. Those flags are solver implementation details only.

They are **not serialized provenance** and are not trusted by the verifier. The verifier independently re-derives the same classification from the result's ordinary musical values.

This keeps the artifact representation decomposed and prevents an opaque label from becoming a source of truth.

## Protected anchors

The v2.8.0a2 modulation repair remains a protected architecture boundary. Certified chromatic functions cannot contaminate anchors where that would undermine:

- source-I/destination-IV pivot identity;
- destination V-I confirmation;
- exact destination-leading-tone presence;
- upward destination-leading-tone resolution;
- strict active-key pitch admission.

v2.11 secondary leading-tone sevenths are excluded from those protected positions.

## Verification routing

The independent verifier routes from the declared feature set while preserving earlier contracts:

- ordinary SATB verification;
- modulation-aware SATB verification;
- borrowed-seventh verification when source-aware sevenths are enabled;
- secondary-leading-tone-triad verification for the v2.10 feature;
- secondary-leading-tone-seventh verification for the v2.11 feature.

The v2.11 verifier explicitly separates exact applied-dominant beats from secondary-seventh candidates before applying CM055–CM057.

## Provenance

Artifact schema and constraint-contract version are both `2.11`.

Semantic provenance commits:

- the full generation specification;
- melody, rhythm, bass, and chord/support degrees;
- SATB voices;
- harmonic kind and inversion;
- local target metadata;
- modal-source metadata;
- persistent key contexts;
- objective-vector metadata.

Because v2.11 function identity is reconstructable from those values, no synthetic secondary-function metadata is needed.

## Search and optimization remain separate

No-good distinctness and objective scalarization do not define musical validity. The verifier checks the hard contract independently of how a candidate was discovered or ranked.

Distinctness dimensions remain orthogonal: melody, rhythm, bass, harmony, voicing, harmonic form, tonicization target, modal source, and key context.

## Version boundaries

Current package: `2.11.0a1`

Current artifact schema: `2.11`

Current constraint contract: `2.11`

Current hard-rule range: `CM001-CM057`

Deliberately deferred: half-diminished secondary leading-tone sevenths, third-inversion seventh semantics, arbitrary modulation chains, distant/enharmonic modulation, broad enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, and probabilistic key/function inference.
