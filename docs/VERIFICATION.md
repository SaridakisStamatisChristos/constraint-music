# Verification model

Constraint Music v2.12 defines 57 stable hard musical rules (`CM001–CM057`). The verifier checks them from ordinary serialized musical values plus the generation specification, without rerunning CP-SAT and without inspecting solver variables or trusting solver-only function/quality witnesses.

## Contract layers

- `CM001–CM016` — tonal/harmonic foundation: shape, active-key pitch domains, harmony domain, strong-beat melody/bass membership, progression legality, melodic/bass motion limits, tritone avoidance, tendency-tone resolution, repetition, leap recovery, parallel-perfect avoidance, and backward-compatible whole-piece closure.
- `CM017–CM021` — rhythm, tie/rest grammar, bar density, motif relations, and terminal articulation.
- `CM022–CM026` — phrase boundaries, roles, structural relations, phrase-local cadences, and antecedent/consequent structure.
- `CM027–CM032` — solver-native SATB shape, ranges/order, spacing, complete triadic realization/root doubling, inner-voice parallel-perfect avoidance, and active-key leading-tone resolution.
- `CM033–CM036` — harmonic kind/inversion metadata, complete active-key seventh realization, chordal-seventh descent, and ordinary dominant-seventh behavior.
- `CM037–CM040` — exact applied-dominant tonicization.
- `CM041–CM042` — modal-mixture context and borrowed-triad realization.
- `CM043–CM048` — persistent local-key context and the certified dominant-key modulation boundary.
- `CM049–CM051` — borrowed-seventh context, source-derived four-tone realization, and source-aware tendencies.
- `CM052–CM054` — secondary leading-tone triad context/support, realization, and target/tendency resolution.
- `CM055–CM057` — complete secondary leading-tone seventh context/quality, exact four-tone realization/inversion, and exact target/tendency resolution.

Search and objective semantics never waive hard rules.

## Solver/verifier symmetry

Every hard musical consequence introduced by the solver has a separately implemented post-solve check. Configuration validation may reject malformed declarations before model construction, but certification never trusts that a CP-SAT constraint was present merely because the solver returned `OPTIMAL` or `FEASIBLE`.

For SATB and harmonic context, the verifier receives ordinary MIDI-note arrays, stored functional/support degrees, chord-kind/inversion metadata, nullable local targets, nullable modal sources, and—when modulation is enabled—explicit per-beat key contexts. It reconstructs pitch classes and context-derived harmonic identities independently.

A solver assignment that fails this pass raises `InternalVerificationError` and is not exported as verified output.

## Exact active-key interpretation

The artifact/global key remains immutable, but v2.8 introduced persistent active-key state. When modulation is enabled, melodic, bass, harmonic, modal-source, local-target, and objective interpretation use the exact source-before/destination-after context declared by the specification.

The solver may use a source/destination union storage domain internally, but neither compiler nor verifier treats that union as unrestricted chromatic permission.

## Scoped chromatic exception in v2.12

Historically CM002/CM003/CM005/CM006 were entirely diatonic/support-triad based. A real third-inversion secondary leading-tone seventh can place its chordal seventh in the bass, and that tone may be chromatic to the active key.

v2.12 handles this without weakening ordinary harmony:

1. the expanded outer-voice domain is selected only when the secondary-seventh feature is enabled;
2. ordinary beats retain the earlier active-key/support contract;
3. a chromatic strong soprano or bass is accepted only if that beat first independently reconstructs as an exact secondary leading-tone seventh;
4. malformed target-bearing chords receive no generic chromatic exemption;
5. inversion `3` is accepted only on a beat independently reconstructed as a secondary leading-tone seventh.

This makes `42` represent an actual seventh-in-bass sonority rather than a metadata exception.

## Applied-dominant verification

A target-bearing seventh is not automatically an applied dominant.

A beat counts as an applied dominant only when the verifier independently reconstructs:

1. a non-null supported local target;
2. `ChordKind.SEVENTH`;
3. the correct active-key applied-dominant root/support identity;
4. all four target-derived `V7/x` pitch classes exactly once;
5. a supported inversion whose bass agrees with the reconstructed chord.

CM039 checks immediate resolution to the declared untargeted local tonic. CM040 checks chordal-seventh descent and local-leading-tone ascent.

`minimum_applied_dominants` counts only exact `V7/x` realizations. Secondary leading-tone triads and sevenths cannot counterfeit the minimum.

## Borrowed harmony

For source-bearing harmony, the verifier derives the canonical parallel source rather than trusting a name. Borrowing and local-target identity remain mutually exclusive on the same beat, and certified cadence/modulation anchors remain protected.

Borrowed-seventh semantics remain governed by CM049–CM051 and their existing filtered inversion/source policy; v2.12's new third-inversion exception is not a blanket change to every seventh family.

## Secondary leading-tone triad verification

CM052–CM054 independently reconstruct the v2.10 `vii°/x` triad from active key, target, support degree, SATB pitch content, inversion, and immediate target resolution. v2.12 does not weaken that triad contract.

## Complete secondary leading-tone seventh verification — v2.12

A target-bearing seventh that is not an exact applied dominant becomes a secondary-leading-tone candidate only when the seventh feature is enabled. No serialized quality label is trusted.

### CM055 — context and quality eligibility

The verifier checks:

- a supported non-tonic target in the exact active local key;
- deterministic progression-compatible support degree;
- no modal-source overlap;
- no protected cadence/modulation-anchor contamination;
- separation from exact applied-dominant identity;
- target-quality eligibility.

For a **major local target**, both fully diminished and half-diminished qualities are eligible. For a **minor local target**, the certified quality is fully diminished. Diminished and augmented target triads are outside this tonicization subsystem.

The support degree is a structural progression-graph bridge, not a proxy for chord identity. v2.12 does not impose v2.11's old two-pitch diatonic-overlap threshold on secondary sevenths; exact target-derived pitch reconstruction determines the musical function.

### CM056 — exact realization and inversion

The verifier derives each eligible pitch set from target + active key and requires:

- all four target-derived pitch classes exactly once;
- independently reconstructed fully diminished or half-diminished quality;
- inversion in `0..3` for that reconstructed secondary seventh;
- actual bass pitch class equal to the reconstructed inversion member.

The generic inversion-scope guard separately rejects inversion `3` on non-secondary beats, even while the feature is enabled.

### CM057 — exact target and tendency resolution

Every certified secondary leading-tone seventh resolves immediately to its declared untargeted, unborrowed triadic target. Each SATB carrier is checked independently:

- local leading tone/root: `+1` semitone;
- diminished fifth: `-1` semitone for a major target, `-2` for a minor target;
- fully diminished chordal seventh: `-1` semitone;
- half-diminished chordal seventh: `-2` semitones.

These checks apply to soprano, alto, tenor, and bass, including the seventh-bearing bass of `vii°42/x` and `viiø42/x`.

After modulation, reconstruction uses the persistent destination active key. A stale global-key interpretation fails closed.

## Modulation verification and v2.8.0a2 strictness

The certified modulation model supports one same-mode dominant-key modulation with a fixed common-chord pivot. The destination context persists from the declared boundary through the end of the artifact.

The strict v2.8.0a2 architecture never skips terminal tendency-tone rules to regain feasibility. CM047 independently confirms the terminal destination V-I, unborrowed/untargeted cadence identity, destination-tonic outer voices, final articulation, destination-leading-tone presence, and upward semitone resolution in every SATB voice carrying it.

v2.12 does not weaken this boundary. Secondary leading-tone triads and sevenths cannot occupy protected pivot or destination-cadence anchors.

## Search-objective verification

Optimization preferences remain outside the hard musical contract. The minimized objective vector remains:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

The vector is independently recomputed from finished musical values. Compiled and reconstructed vectors must agree exactly or generation fails closed.

No-good distinctness dimensions remain orthogonal: `melody`, `rhythm`, `bass`, `harmony`, `voicing`, `harmonic_form`, `tonicization`, `modal_source`, and `key_context`.

## Artifact integrity

A current v2.12 JSON artifact carries:

- artifact schema version `2.12`;
- constraint-contract version `2.12`;
- SHA-256 of the canonical `CM001–CM057` contract;
- SHA-256 of the semantic specification and musical result;
- SATB voice arrays;
- harmonic kind/inversion metadata when present;
- local-target metadata when present;
- modal-source metadata when present;
- key-context metadata when present;
- independently recomputable objective-vector metadata;
- SHA-256 of the complete serialized spec/solver/validation/music/search payload;
- IDs of the hard constraints checked at generation time.

Secondary-seventh quality/function identity requires no opaque serialized field. Target + harmonic form + active key + support degree + SATB realization already determine the certified identity. Tampering with target, voicing, inversion, modal source, key context, or feature specification is detectable by provenance and/or musical verification.

`constraint-music verify artifact.json` checks musical validity plus current provenance. `--allow-legacy` remains available for intentional inspection of older artifacts whose schema/contract predates the current verifier.

## Validation baseline

The pre-merge v2.12 branch passes the full gate on Python 3.11, 3.12, and 3.13:

- Ruff clean;
- strict mypy clean across 27 source files;
- 197 tests passing;
- 80% branch-aware coverage;
- source distribution and wheel build successful.

The validation matrix includes every chromatic tonic in both major and minor modes, every progression-reachable eligible local target under the default graph, each certified quality, and all four inversions. The adversarial suite additionally covers inversion-scope leakage, missing/duplicated tones, quality-specific tendency errors, applied-dominant count confusion, modal overlap, protected anchors, provenance tampering, destination-key reconstruction, stale-key forgery, and the former support-overlap exclusion.

## Historical payloads

Payloads that predate v2.5 may omit harmonic-form arrays. Pre-v2.6 payloads may omit local targets. Pre-v2.7 payloads may omit modal sources. Pre-v2.8 payloads may omit key contexts.

Constraint Music does not synthesize fictional modern metadata for those artifacts. Missing context metadata is acceptable only when the loaded specification does not require the corresponding feature.

## Claim boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint compliance demonstrates conformance to the declared executable contract; it does not prove aesthetic quality, perceptual optimality, or complete historical-style authenticity.

v2.12 completes the secondary leading-tone seventh family claimed by this subsystem. Arbitrary modulation chains, distant/enharmonic modulation, broad enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, free key-center inference, and probabilistic harmony certification remain separate future domains. Pareto mode returns candidates nondominated within its explored pool; it does not prove the global Pareto frontier.
