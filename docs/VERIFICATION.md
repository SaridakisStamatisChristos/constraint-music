# Verification model

Constraint Music v2.10 defines 54 stable hard musical rules (`CM001–CM054`). The verifier checks them from ordinary serialized musical values plus the generation specification, without rerunning CP-SAT and without inspecting solver variables or constraints.

## Contract layers

`CM001–CM016` retain the tonal/harmonic foundation: shape, active-key pitch domains, harmony domain, strong-beat melody/bass chord membership, progression legality, melodic/bass motion limits, tritone avoidance, tendency-tone resolution, repetition, leap recovery, parallel-perfect avoidance, and the backward-compatible whole-piece closure rule.

`CM017–CM021` certify rhythm, tie/rest grammar, bar density, motif relations, and terminal articulation.

`CM022–CM026` certify phrase boundaries, roles, structural relations, phrase-local cadences, and answer-linked antecedent/consequent structure.

`CM027–CM032` certify the solver-native SATB layer: beat shape and soprano anchoring, ranges/order, spacing, complete triadic realization/root doubling, inner-voice parallel-perfect avoidance, and active-key inner leading-tone resolution.

`CM033–CM036` certify the v2.5 harmonic-form layer: explicit kind/inversion metadata, complete active-key seventh realization and inversion agreement, chordal-seventh downward resolution, and dominant-seventh resolution.

`CM037–CM040` certify v2.6 applied-dominant tonicization. In v2.10 these rules apply to target-bearing seventh forms; target-bearing triads are separately certified by CM052–CM054.

`CM041–CM042` certify modal-mixture context and borrowed-triad realization. Source-bearing sevenths route to the additive v2.9 rule family.

`CM043–CM048` certify v2.8 persistent-key modulation:

- `CM043` — one explicit key context per beat;
- `CM044` — declared same-mode dominant destination and boundary;
- `CM045` — certified source-I/destination-IV common-chord pivot;
- `CM046` — post-boundary harmony reconstructed in the persistent destination key;
- `CM047` — strict destination V-I confirmation, including destination-leading-tone presence and upward resolution in every SATB carrier;
- `CM048` — exact serialized key-context sequence.

v2.9 adds three borrowed-seventh rules:

- `CM049` — borrowed-seventh context/eligibility;
- `CM050` — exact source-derived four-tone realization and inversion;
- `CM051` — borrowed seventh/source tendency resolution.

v2.10 adds three secondary leading-tone rules:

- `CM052` — supported local target, deterministic support degree, no modal overlap, and no protected-anchor overlap;
- `CM053` — complete target-derived diminished triad with tendency tones undoubled, stable third doubled, and inversion/bass agreement;
- `CM054` — immediate unaltered triadic target plus local leading-tone and diminished-fifth resolution.

## Solver/verifier symmetry

Every hard musical consequence introduced by the solver has a separately implemented post-solve check. Configuration validation may reject malformed declarations before model construction, but certification never trusts that a CP-SAT constraint was present merely because the solver returned `OPTIMAL` or `FEASIBLE`.

For SATB and harmonic context, the verifier receives ordinary MIDI-note arrays, stored functional/support chord degrees, chord-kind/inversion metadata, nullable local targets, nullable modal sources, and—when modulation is enabled—explicit per-beat key contexts. It reconstructs pitch classes and context-derived harmonic identities independently.

A solver assignment that fails this pass raises `InternalVerificationError` and is not exported as verified output.

## Active-key domain verification

The artifact/global key remains immutable, but v2.8 introduced persistent active-key state. When modulation is enabled:

- CM002 validates every melody step against the exact active key at that beat;
- CM003 validates every bass beat against the exact active key;
- harmonic interpretation, modal-source derivation, local-target derivation, and objective tension use that same active context.

The solver may store modulation-enabled pitches in the union of explicitly declared source/destination key domains, but the verifier never treats that union as global chromatic permission.

When modulation is disabled, legacy global-key behavior is preserved.

## Preserved outer-voice semantics

CM005 and CM006 continue to require strong melody/soprano and bass to belong to the active-key triadic core identified by the stored degree.

Tonicization, borrowed harmony, modulation, and v2.10 secondary leading-tone harmony therefore cannot silently reinterpret the outer-voice contract. The theory layer admits only contexts representable under that invariant.

For a secondary leading-tone chord, the stored degree is a compatibility support degree rather than the chromatic diminished root. The verifier independently recomputes the correct support degree from active key, target, and configured progression graph, then separately verifies the actual diminished sonority.

## Applied-dominant verification

A target-bearing seventh is an applied dominant. The verifier independently reconstructs its target-derived dominant seventh, root identity, inversion, immediate local-tonic resolution, chordal-seventh descent, and local-leading-tone ascent.

The applied-dominant minimum counts target-bearing sevenths only. A v2.10 target-bearing triad cannot satisfy `minimum_applied_dominants`.

## Borrowed-triad verification

For a source-bearing triad, the verifier independently derives the canonical parallel source, source scale, source triad on the serialized degree, and expected bass pitch class from inversion. It requires no simultaneous local target and complete source-derived triadic pitch content. Certified context/cadence anchors remain unborrowed.

## Borrowed-seventh verification

For a source-bearing seventh, the v2.9 verifier first establishes CM049 eligibility, then independently derives the complete source seventh from active key + source + degree. It does not trust solver relation rows or display names.

CM050 requires all four expected pitch classes exactly once. The serialized inversion must be 0, 1, or 2 and agree with the realized bass.

CM051 independently requires every carried borrowed chordal seventh to descend by one or two semitones and any admitted parallel-major source leading tone to ascend by one semitone.

## Secondary leading-tone verification

A target-bearing triad is interpreted as a v2.10 secondary leading-tone chord only when the feature is enabled. The verifier does not trust an opaque chord label. It reconstructs the chord from ordinary semantic fields.

For every such beat it independently:

1. obtains the exact active key at that beat;
2. verifies that the serialized target is a supported non-tonic major/minor diatonic target;
3. recomputes the deterministic CM005/CM006/CM007-compatible support degree;
4. derives the diminished triad rooted one semitone below the target;
5. verifies complete pitch content, exact tendency-tone counts, stable-third doubling, and inversion/bass agreement;
6. verifies that the next chord is the declared untargeted, unborrowed triadic target;
7. checks every local-leading-tone carrier for +1 semitone resolution;
8. checks every diminished-fifth carrier for -1 or -2 semitone resolution.

CM052 rejects unsupported/forged targets, wrong support degrees, modal-source overlap, final-position use, and protected modulation/cadence-anchor use.

CM053 rejects incomplete sonorities, doubled local tendency tones, wrong stable-tone doubling, invalid inversion, and bass/inversion mismatch.

CM054 rejects wrong/missing targets and wrong-direction tendency resolution.

Post-modulation verification reconstructs the diminished sonority from the destination active key. A stale global-key interpretation fails closed.

## Modulation verification and v2.8.0a2 strictness

The certified modulation model supports exactly one same-mode dominant-key modulation with a fixed common-chord pivot. The destination context persists from the declared boundary through the end of the artifact.

The strict v2.8.0a2 architecture never skips terminal CM032 to regain feasibility. Instead, storage domains were repaired to admit destination accidentals in outer voices while exact per-step active-key gating prevents region leakage.

CM047 independently confirms the terminal destination V-I, unborrowed/untargeted cadence identity, destination-tonic outer voices, final articulation, presence of the destination leading tone on the dominant, and upward semitone resolution in every SATB voice carrying that leading tone.

v2.10 does not weaken this boundary. Secondary leading-tone chords cannot occupy the certified pivot or terminal destination cadence anchors.

## Search-objective verification

Optimization preferences remain outside the hard musical contract. The minimized objective vector remains:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

The vector is independently recomputed from finished musical values. Compiled and reconstructed vectors must agree exactly or generation fails closed.

No-good distinctness dimensions remain orthogonal search semantics: `melody`, `rhythm`, `bass`, `harmony`, `voicing`, `harmonic_form`, `tonicization`, `modal_source`, and `key_context`.

## Artifact integrity

A current v2.10 JSON artifact carries:

- artifact schema version `2.10`;
- constraint-contract version `2.10`;
- SHA-256 of the canonical `CM001–CM054` contract;
- SHA-256 of the semantic specification and musical result;
- SATB voice arrays;
- harmonic kind/inversion metadata when present;
- local target metadata when present;
- modal-source metadata when present;
- key-context metadata when present;
- independently recomputable objective-vector metadata;
- SHA-256 of the complete serialized spec/solver/validation/music/search payload;
- IDs of the hard constraints checked at generation time.

Secondary leading-tone identity requires no new opaque serialized field: target + harmonic form + active key + stored support degree + SATB realization are already committed. Changing a target while leaving notes untouched is detectable as provenance tampering.

`constraint-music verify artifact.json` checks musical validity plus current provenance. `--allow-legacy` remains available when intentionally inspecting older artifacts whose schema/contract predates the current verifier.

## Historical payloads

Payloads that predate v2.5 may omit harmonic-form arrays. Pre-v2.6 payloads may omit local targets. Pre-v2.7 payloads may omit modal sources. Pre-v2.8 payloads may omit key contexts.

Constraint Music does not synthesize fictional modern metadata for those artifacts. Missing context metadata is acceptable only when the loaded specification does not require the corresponding feature.

## Claim boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint compliance demonstrates conformance to the declared executable contract; it does not prove aesthetic quality, perceptual optimality, or complete historical-style authenticity.

v2.10 certifies a deliberately narrow secondary leading-tone **triad** model. It does not certify secondary leading-tone seventh chords, third-inversion sevenths, arbitrary modulation chains, enharmonic reinterpretation, augmented-sixth or Neapolitan reinterpretation, free key-center inference, or probabilistic harmony certification. Pareto mode returns candidates nondominated within its explored pool; it does not prove the global Pareto frontier.
