# Verification model

Constraint Music v2.9 defines 51 stable hard musical rules (`CM001–CM051`). The verifier checks them from ordinary serialized musical values plus the generation specification, without rerunning CP-SAT and without inspecting solver variables or constraints.

## Contract layers

`CM001–CM016` retain the tonal/harmonic foundation: shape, active-key pitch domains, harmony domain, strong-beat melody/bass chord membership, progression legality, melodic/bass motion limits, tritone avoidance, tendency-tone resolution, repetition, leap recovery, parallel-perfect avoidance, and the backward-compatible whole-piece closure rule.

`CM017–CM021` certify rhythm, tie/rest grammar, bar density, motif relations, and terminal articulation.

`CM022–CM026` certify phrase boundaries, roles, structural relations, phrase-local cadences, and answer-linked antecedent/consequent structure.

`CM027–CM032` certify the solver-native SATB layer: beat shape and soprano anchoring, ranges/order, spacing, complete triadic realization/root doubling, inner-voice parallel-perfect avoidance, and active-key inner leading-tone resolution.

`CM033–CM036` certify the v2.5 harmonic-form layer: explicit kind/inversion metadata, complete active-key seventh realization and inversion agreement, chordal-seventh downward resolution, and dominant-seventh resolution.

`CM037–CM040` certify v2.6 tonicization: target context, exact applied-dominant realization, immediate target resolution, and local tendency-tone resolution.

`CM041–CM042` certify modal-mixture context and borrowed-triad realization. v2.9 keeps those triad semantics intact while CM041 now routes eligible source-bearing sevenths to the new additive rule family.

`CM043–CM048` certify v2.8 persistent-key modulation:

- `CM043` — one explicit key context per beat;
- `CM044` — declared same-mode dominant destination and boundary;
- `CM045` — certified source-I/destination-IV common-chord pivot;
- `CM046` — post-boundary harmony reconstructed in the persistent destination key;
- `CM047` — strict destination V-I confirmation, including destination-leading-tone presence and upward resolution in every SATB carrier;
- `CM048` — exact serialized key-context sequence.

v2.9 adds three borrowed-seventh rules:

- `CM049` — borrowed-seventh context/eligibility: canonical active-key source, supported degree, no tonicization overlap, and no certified pivot/cadence anchor overlap;
- `CM050` — source-derived realization: all four source-derived pitch classes exactly once plus root/first/second inversion agreement with bass;
- `CM051` — tendency resolution: borrowed chordal seventh descends by step and any admitted parallel-major source leading tone ascends by semitone in every SATB carrier.

## Solver/verifier symmetry

Every hard musical consequence introduced by the solver has a separately implemented post-solve check. Configuration validation may reject malformed declarations before model construction, but certification never trusts that a CP-SAT constraint was present merely because the solver returned `OPTIMAL` or `FEASIBLE`.

For SATB and harmonic context, the verifier receives ordinary MIDI-note arrays, functional chord degrees, chord-kind/inversion metadata, nullable tonicization targets, nullable modal sources, and—when modulation is enabled—explicit per-beat key contexts. It reconstructs pitch classes and context-derived harmonic identities independently.

A solver assignment that fails this pass raises `InternalVerificationError` and is not exported as verified output.

## Active-key domain verification

The artifact/global key remains immutable, but v2.8 introduced persistent active-key state. When modulation is enabled:

- CM002 validates every melody step against the exact active key at that beat;
- CM003 validates every bass beat against the exact active key;
- harmonic interpretation, modal-source derivation, tonicization, and objective tension use that same active context.

The solver may store modulation-enabled pitches in the union of explicitly declared source/destination key domains, but the verifier never treats that union as global chromatic permission.

When modulation is disabled, legacy global-key behavior is preserved.

## Preserved outer-voice semantics

CM005 and CM006 continue to require strong melody/soprano and bass to belong to the triadic core identified by functional degree in the exact active local key.

Tonicization, borrowed harmony, and modulation therefore cannot silently reinterpret the outer-voice contract. The theory layer admits only contexts representable under that invariant.

This is why v2.9 borrowed sevenths use a structural whitelist rather than accepting every source-mode seventh.

## Borrowed-triad verification

For a source-bearing triad, the verifier independently derives:

1. the canonical parallel source allowed by the active key mode;
2. the source scale on the active tonic;
3. the source triad on the serialized functional degree;
4. the expected bass pitch class from the serialized inversion.

It requires no simultaneous tonicization target and complete source-derived triadic pitch content. Certified context/cadence anchors remain unborrowed.

## Borrowed-seventh verification

For a source-bearing seventh, the v2.9 verifier first establishes CM049 eligibility, then independently derives the complete source seventh from active key + source + degree. It does not trust solver relation rows or display names.

CM050 requires all four expected pitch classes exactly once. A duplicated tone replacing a required seventh member is invalid even if the voicing would otherwise look plausible. The serialized inversion must be 0, 1, or 2 and its expected chord member must be the realized bass pitch class.

CM051 independently examines all SATB voices on the following transition:

- each carrier of the source-derived chordal seventh must descend by one or two semitones;
- when the canonical source is parallel major, any carried source leading tone admitted by the certified chord must ascend by one semitone.

A source-bearing seventh serialized as ordinary diatonic harmony fails closed under the ordinary seventh rules; an ordinary seventh falsely serialized as borrowed fails CM050.

## Modulation verification and v2.8.0a2 strictness

The certified modulation model supports exactly one same-mode dominant-key modulation with a fixed common-chord pivot. The destination context persists from the declared boundary through the end of the artifact.

The strict v2.8.0a2 architecture never skips terminal CM032 to regain feasibility. Instead, storage domains were repaired to admit destination accidentals in outer voices while exact per-step active-key gating prevents region leakage.

CM047 independently confirms the terminal destination V-I, unborrowed/untargeted cadence identity, destination-tonic outer voices, final articulation, presence of the destination leading tone on the dominant, and upward semitone resolution in every SATB voice carrying that leading tone.

v2.9 does not weaken this boundary. Borrowed sevenths cannot occupy the pivot or terminal destination cadence.

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

A current v2.9 JSON artifact carries:

- artifact schema version `2.9`;
- constraint-contract version `2.9`;
- SHA-256 of the canonical `CM001–CM051` contract;
- SHA-256 of the semantic specification and musical result;
- SATB voice arrays;
- harmonic kind/inversion metadata when present;
- tonicization-target metadata when present;
- modal-source metadata when present;
- key-context metadata when present;
- independently recomputable objective-vector metadata;
- SHA-256 of the complete serialized spec/solver/validation/music/search payload;
- IDs of the hard constraints checked at generation time.

The composition digest commits modal-source identity, harmonic form, tonicization, and persistent key contexts. Changing a semantic declaration while leaving notes untouched is detectable as provenance tampering.

`constraint-music verify artifact.json` checks musical validity plus current provenance. `--allow-legacy` remains available when intentionally inspecting older artifacts whose schema/contract predates the current verifier.

## Historical payloads

Payloads that predate v2.5 may omit harmonic-form arrays. Pre-v2.6 payloads may omit tonicization targets. Pre-v2.7 payloads may omit modal sources. Pre-v2.8 payloads may omit key contexts.

Constraint Music does not synthesize fictional modern metadata for those artifacts. Missing context metadata is acceptable only when the loaded specification does not require the corresponding feature.

## Claim boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint compliance demonstrates conformance to the declared executable contract; it does not prove aesthetic quality, perceptual optimality, or complete historical-style authenticity.

v2.9 certifies a deliberately narrow borrowed-seventh subset. It does not certify secondary leading-tone chords, third-inversion sevenths, arbitrary modulation chains, enharmonic reinterpretation, augmented-sixth or Neapolitan reinterpretation, free key-center inference, or probabilistic harmony certification. Pareto mode returns candidates nondominated within its explored pool; it does not prove the global Pareto frontier.
