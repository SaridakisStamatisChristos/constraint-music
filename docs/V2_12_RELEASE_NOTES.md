# Constraint Music v2.12 release notes

v2.12 completes the verifier-certified secondary leading-tone seventh subsystem within Constraint Music's declared common-practice tonicization domain.

## Certified family

For a **major local target**, the solver and independent verifier certify both fully diminished and half-diminished leading-tone sevenths in every inversion:

- `vii°7/x`, `vii°65/x`, `vii°43/x`, `vii°42/x`
- `viiø7/x`, `viiø65/x`, `viiø43/x`, `viiø42/x`

For a **minor local target**, the certified family is the fully diminished form in every inversion:

- `vii°7/x`, `vii°65/x`, `vii°43/x`, `vii°42/x`

Diminished and augmented target triads remain outside secondary tonicization rather than being misclassified as local tonics.

## Verification model

Quality is not trusted as serialized metadata. The independent verifier reconstructs the function from the exact active key, local target, deterministic support degree, four SATB pitch classes, inversion/bass agreement, and absence of modal-source identity. Applied `V7/x`, fully diminished `vii°7/x`, and eligible half-diminished `viiø7/x` therefore remain distinct by musical identity rather than by an opaque label.

The third inversion is a real `42`, not merely inversion metadata: the chordal seventh must be present in the bass. Inversion `3` remains illegal for ordinary chords on this execution path and is admitted only when the beat independently reconstructs as a secondary leading-tone seventh.

## Voice leading

CM057 uses exact target- and quality-dependent tendency semantics in every SATB voice, including the bass:

- local leading tone/root: `+1` semitone;
- diminished fifth: `-1` for a major target, `-2` for a minor target;
- fully diminished chordal seventh: `-1` semitone;
- half-diminished chordal seventh: `-2` semitones.

Every certified secondary leading-tone seventh resolves immediately to its declared untargeted, unborrowed triadic target.

## Compatibility boundary

The expanded chromatic outer-voice domain is routed only when `secondary_leading_tone_seventh_enabled: true`. Ordinary harmony and specifications with the feature disabled retain their established compiler/verifier paths. This avoids granting unrestricted chromatic permission merely to support `42`.

## Adversarial gates

The v2.12 suite explicitly covers:

- both certified qualities across all four inversions;
- missing and duplicated chord members;
- inversion/bass mismatch;
- illegal third inversion on a non-secondary chord;
- wrong quality-specific seventh resolution;
- wrong diminished-fifth and local-leading-tone resolution;
- applied-dominant count confusion;
- modal-source overlap;
- cadence/modulation-anchor contamination;
- provenance target tampering;
- persistent destination-key reconstruction after modulation;
- stale global-key counterfeit interpretation.

## Version and validation baseline

- package: `2.12.0a1`
- artifact schema: `2.12`
- constraint contract: `2.12`
- hard rules: `CM001–CM057`
- tests: **147 passing**
- branch-aware coverage: **80%**
- strict mypy: clean across **27 source files**
- CI: Ruff, mypy, pytest/coverage, and package build pass on Python **3.11, 3.12, and 3.13**
