# Verification model

Constraint Music v2.7 defines 42 stable hard musical rules (`CM001`–`CM042`). The verifier checks them from ordinary serialized musical values plus the generation specification, without rerunning CP-SAT and without inspecting solver variables or constraints.

## Contract layers

`CM001`–`CM016` retain the original tonal/harmonic contract: shape, pitch domains, harmony domain, strong-beat melody/bass chord membership, progression legality, melodic/bass motion limits, tritone avoidance, tendency-tone resolution, repetition, leap recovery, parallel-perfect avoidance, and the backward-compatible whole-piece closure rule.

`CM017`–`CM021` certify rhythm, tie/rest grammar, bar density, motif relations, and terminal articulation.

`CM022`–`CM026` certify phrase boundaries, roles, structural relations, phrase-local cadences, and answer-linked antecedent/consequent structure.

`CM027`–`CM032` certify the solver-native SATB layer: beat shape and soprano anchoring, ranges/order, spacing, complete global triadic realization/root doubling, inner-voice parallel-perfect avoidance, and inner leading-tone resolution.

`CM033`–`CM036` certify the v2.5 harmonic-form layer: explicit chord kind/inversion metadata, complete global seventh realization and inversion agreement, chordal-seventh downward resolution, and global dominant-seventh resolution.

`CM037`–`CM040` certify v2.6 tonicization: target context, exact applied-dominant realization, immediate target resolution, and local tendency-tone resolution.

v2.7 adds two modal-mixture rules:

- `CM041` — modal mixture context: enabled artifacts carry one nullable source per beat; non-null sources are the canonical parallel source, use a supported degree and triadic form, cannot overlap tonicization, remain outside the preserved global cadential boundary, and satisfy `minimum_borrowed_chords`;
- `CM042` — borrowed chord realization: source-mode pitch classes are recomputed from tonic/source/degree, the complete source triad is present, and serialized inversion agrees with the realized bass.

## Solver/verifier symmetry

Every hard musical consequence introduced by the solver has a separately implemented post-solve check. Configuration validation may reject malformed declarations before model construction, but certification never trusts that a CP-SAT constraint was present merely because the solver returned `OPTIMAL` or `FEASIBLE`.

For SATB and harmonic context, the verifier receives ordinary MIDI-note arrays, global chord degrees, chord-kind/inversion metadata, nullable tonicization targets, and nullable modal sources. It reconstructs pitch classes and context-derived harmonic identities independently.

A solver assignment that fails this pass raises `InternalVerificationError` and is not exported as verified output.

## Preserved outer-voice semantics

v2.7 deliberately does not reinterpret `CM005` or `CM006`.

- `CM005` still requires the strong-grid melody/soprano to belong to the global diatonic triad identified by `chord_degrees[beat]`.
- `CM006` still requires bass to belong to that same global diatonic triad.

Applied-dominant and borrowed chromatic tones therefore occur in inner voices. Harmonic contexts are exposed only when they can be represented completely while preserving those historical outer-voice rules.

This boundary is important for artifact compatibility: v2.7 expands harmonic context without changing the meaning of any earlier rule ID.

## Modal-mixture verification

For a non-null modal source, the verifier independently derives:

1. the canonical parallel source allowed by the global mode;
2. the source scale on the same tonic;
3. the source triad on the serialized global functional degree;
4. the expected bass pitch class implied by the serialized inversion.

It requires a triadic form, no simultaneous tonicization target, and all three source-derived pitch classes in the four SATB voices. The borrowed beat may contain one doubled chord tone; unlike global CM030 triads, v2.7 does not impose global-root doubling on a borrowed source triad.

The final beat must remain global. When `require_authentic_cadence` is enabled, the penultimate beat must also remain global. These checks prevent modal mixture from silently changing the established closure contract.

## Search-objective verification

Optimization preferences remain outside the hard musical contract. The model exposes five minimized objective components:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

A separate application-level function reconstructs the same objective vector from finished musical values. Compiled and independently reconstructed vectors must agree exactly or generation fails closed.

No-good distinctness dimensions also remain search semantics rather than hard-rule semantics. v2.7 preserves `melody`, `rhythm`, `bass`, `harmony`, `voicing`, `harmonic_form`, and `tonicization`, and adds `modal_source` for the nullable source-mode sequence.

## Artifact integrity

A current v2.7 JSON artifact carries:

- artifact schema version `2.7`;
- constraint-contract version `2.7`;
- SHA-256 of the canonical `CM001`–`CM042` contract;
- SHA-256 of the semantic specification and musical result;
- SATB soprano/alto/tenor arrays;
- harmonic kind/inversion metadata when present;
- tonicization-target metadata when present;
- modal-source metadata when present;
- independently recomputable objective-vector metadata;
- SHA-256 of the complete serialized spec/solver/validation/music/search payload;
- IDs of the hard constraints checked at generation time.

The semantic composition digest commits modal-source identity as well as tonicization and harmonic-form metadata. Changing a source declaration while leaving notes untouched is therefore detectable as provenance tampering.

`constraint-music verify artifact.json` checks musical validity plus current provenance. `--allow-legacy` remains available when intentionally inspecting older artifacts whose schema/contract predates the current verifier.

## Historical payloads

SATB payloads that predate v2.5 may omit harmonic-form arrays. Payloads that predate v2.6 may omit tonicization targets. Payloads that predate v2.7 may omit modal sources. Constraint Music does not synthesize fictional metadata for those artifacts.

Missing modal-source metadata is accepted only when the loaded specification has modal mixture disabled; a current modal-mixture-enabled artifact must carry explicit source data and fails `CM041` otherwise.

## Claim boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint compliance demonstrates conformance to the declared executable contract; it does not prove aesthetic quality, perceptual optimality, or complete historical-style authenticity.

v2.7 certifies bounded modal mixture through explicit parallel-source borrowed triads. It does not yet certify borrowed sevenths, secondary leading-tone chords, persistent local-key regions, pivot-chord modulation, arbitrary chromatic harmony, or third-inversion sevenths. Pareto mode returns candidates nondominated within its explored pool; it does not prove enumeration of the global mathematical Pareto frontier.
