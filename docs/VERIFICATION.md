# Verification model

Constraint Music v2.11 defines 57 stable hard musical rules (`CM001–CM057`). The verifier checks them from ordinary serialized musical values plus the generation specification, without rerunning CP-SAT and without inspecting solver variables or constraints.

## Contract layers

- `CM001–CM016` — tonal/harmonic foundation: shape, exact active-key pitch domains, harmony domain, strong-beat melody/bass chord membership, progression legality, melodic/bass motion limits, tritone avoidance, tendency-tone resolution, repetition, leap recovery, parallel-perfect avoidance, and the backward-compatible whole-piece closure rule.
- `CM017–CM021` — rhythm, tie/rest grammar, bar density, motif relations, and terminal articulation.
- `CM022–CM026` — phrase boundaries, roles, structural relations, phrase-local cadences, and antecedent/consequent structure.
- `CM027–CM032` — solver-native SATB shape, ranges/order, spacing, complete triadic realization/root doubling, inner-voice parallel-perfect avoidance, and active-key leading-tone resolution.
- `CM033–CM036` — harmonic kind/inversion metadata, complete active-key seventh realization, chordal-seventh descent, and ordinary dominant-seventh behavior.
- `CM037–CM040` — exact applied-dominant tonicization.
- `CM041–CM042` — modal-mixture context and borrowed-triad realization.
- `CM043–CM048` — persistent local-key context and the certified dominant-key modulation boundary.
- `CM049–CM051` — borrowed-seventh context, source-derived four-tone realization, and source-aware tendencies.
- `CM052–CM054` — v2.10 secondary leading-tone triad context/support, realization, and target/tendency resolution.
- `CM055–CM057` — v2.11 secondary leading-tone seventh context/quality, exact four-tone realization/inversion, and target/tendency resolution.

Search and objective semantics never waive hard rules.

## Solver/verifier symmetry

Every hard musical consequence introduced by the solver has a separately implemented post-solve check. Configuration validation may reject malformed declarations before model construction, but certification never trusts that a CP-SAT constraint was present merely because the solver returned `OPTIMAL` or `FEASIBLE`.

For SATB and harmonic context, the verifier receives ordinary MIDI-note arrays, stored functional/support degrees, chord-kind/inversion metadata, nullable local targets, nullable modal sources, and—when modulation is enabled—explicit per-beat key contexts. It reconstructs pitch classes and context-derived harmonic identities independently.

A solver assignment that fails this pass raises `InternalVerificationError` and is not exported as verified output.

## Exact active-key interpretation

The artifact/global key remains immutable, but v2.8 introduced persistent active-key state. When modulation is enabled:

- CM002 validates every melody step against the exact active key at that beat;
- CM003 validates every bass beat against the exact active key;
- harmonic interpretation, modal-source derivation, local-target derivation, and objective tension use that same active context.

The solver may use a source/destination union storage domain internally, but neither the compiler nor verifier treats that union as unrestricted chromatic permission.

## Preserved outer-voice semantics

CM005 and CM006 continue to require strong melody/soprano and bass membership in the active-key triadic core identified by the stored degree.

Chromatic functional families therefore use explicit compatibility bridges instead of silently redefining those rules. For secondary leading-tone harmony, the stored degree is a deterministic support degree rather than the chromatic diminished root. The verifier independently recomputes the support degree from active key, target, and progression graph, then separately verifies the actual chromatic sonority.

## Applied-dominant verification

In v2.11, **target-bearing seventh** is no longer sufficient by itself to mean applied dominant.

A beat counts as an applied dominant only when the verifier can reconstruct all of the following from serialized musical values:

1. a non-null supported local target;
2. `ChordKind.SEVENTH`;
3. the correct active-key applied-dominant root/support degree;
4. all four target-derived `V7/x` pitch classes exactly once;
5. a supported inversion whose bass agrees with the reconstructed chord.

CM039 then checks immediate resolution to the declared untargeted local tonic. CM040 checks chordal-seventh descent and local-leading-tone ascent.

`minimum_applied_dominants` counts only those exact `V7/x` realizations. A v2.10 target-bearing triad or a v2.11 target-bearing fully diminished seventh cannot counterfeit the minimum.

## Borrowed harmony

For a source-bearing triad, the verifier independently derives the canonical parallel source, source scale, source triad on the stored degree, and expected bass pitch class from inversion. No simultaneous local target is allowed.

For a source-bearing seventh, CM049 establishes eligibility, CM050 requires all four source-derived pitch classes exactly once with root/first/second inversion agreement, and CM051 checks borrowed chordal-seventh descent plus any admitted parallel-major source-leading-tone ascent.

Borrowing remains excluded from certified cadence/modulation anchors.

## Secondary leading-tone triad verification — v2.10

A target-bearing triad is interpreted as a v2.10 secondary leading-tone chord only when the feature is enabled. The verifier independently:

1. obtains the exact active key;
2. verifies a supported non-tonic major/minor target;
3. recomputes the CM005/CM006/CM007-compatible support degree;
4. derives the diminished triad rooted one semitone below the target;
5. verifies complete pitch content, exact tendency-tone counts, stable-third doubling, and inversion/bass agreement;
6. verifies immediate resolution to the declared untargeted, unborrowed triadic target;
7. checks every local-leading-tone carrier for +1 semitone resolution;
8. checks every diminished-fifth carrier for -1 or -2 semitone resolution.

CM052–CM054 remain unchanged in v2.11.

## Secondary leading-tone seventh verification — v2.11

A target-bearing seventh that is not an exact applied dominant is a candidate for the v2.11 secondary-leading-tone-seventh family when that feature is enabled. The verifier does not trust a synthetic function label; it reconstructs identity directly.

CM055 independently checks:

- supported non-tonic target in the exact active local key;
- deterministic support degree;
- no modal-source overlap;
- no final-position or protected cadence/modulation-anchor contamination;
- separation from exact applied-dominant identity.

CM056 derives the fully diminished pitch set rooted one semitone below the target and requires:

- all four pitch classes exactly once;
- no duplicated unstable tone;
- root, first, or second inversion only;
- bass/inversion agreement.

Half-diminished quality and third inversion are not certified.

CM057 requires immediate resolution to the declared untargeted, unborrowed triadic target and checks every SATB carrier independently:

- local leading tone: `+1` semitone;
- diminished fifth: `-1` or `-2` semitones;
- chordal diminished seventh: `-1` or `-2` semitones.

After modulation, all reconstruction uses the persistent destination active key. A stale global-key interpretation fails closed.

## Modulation verification and v2.8.0a2 strictness

The certified modulation model supports exactly one same-mode dominant-key modulation with a fixed common-chord pivot. The destination context persists from the declared boundary through the end of the artifact.

The strict v2.8.0a2 architecture never skips terminal tendency-tone rules to regain feasibility. CM047 independently confirms the terminal destination V-I, unborrowed/untargeted cadence identity, destination-tonic outer voices, final articulation, presence of the destination leading tone on the dominant, and upward semitone resolution in every SATB voice carrying it.

v2.11 does not weaken this boundary. Secondary leading-tone triads and sevenths cannot occupy protected pivot or destination-cadence anchors.

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

A current v2.11 JSON artifact carries:

- artifact schema version `2.11`;
- constraint-contract version `2.11`;
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

v2.11 secondary-leading-tone-seventh identity requires no opaque serialized field. Target + harmonic form + active key + support degree + SATB realization are already committed. Tampering with target, voicing, inversion, modal source, key context, or feature specification is detectable by provenance and/or musical verification.

`constraint-music verify artifact.json` checks musical validity plus current provenance. `--allow-legacy` remains available for intentional inspection of older artifacts whose schema/contract predates the current verifier.

## Historical payloads

Payloads that predate v2.5 may omit harmonic-form arrays. Pre-v2.6 payloads may omit local targets. Pre-v2.7 payloads may omit modal sources. Pre-v2.8 payloads may omit key contexts.

Constraint Music does not synthesize fictional modern metadata for those artifacts. Missing context metadata is acceptable only when the loaded specification does not require the corresponding feature.

## Claim boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint compliance demonstrates conformance to the declared executable contract; it does not prove aesthetic quality, perceptual optimality, or complete historical-style authenticity.

v2.11 deliberately does not certify half-diminished secondary leading-tone sevenths, third-inversion sevenths, arbitrary modulation chains, distant/enharmonic modulation, broad enharmonic reinterpretation, augmented-sixth/Neapolitan reinterpretation, free key-center inference, or probabilistic harmony certification. Pareto mode returns candidates nondominated within its explored pool; it does not prove the global Pareto frontier.
