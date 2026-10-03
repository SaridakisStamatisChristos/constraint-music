# Verification model

Constraint Music v2.6 defines 40 stable hard musical rules (`CM001`–`CM040`). The verifier checks them from ordinary serialized musical values plus the generation specification, without rerunning CP-SAT and without inspecting solver variables or constraints.

## Contract layers

`CM001`–`CM016` retain the original tonal/harmonic contract: shape, pitch domains, harmony domain, strong-beat melody/bass chord membership, progression legality, melodic/bass motion limits, tritone avoidance, tendency-tone resolution, repetition, leap recovery, parallel-perfect avoidance, and the backward-compatible whole-piece closure rule.

`CM017`–`CM021` certify rhythm, tie/rest grammar, bar density, motif relations, and terminal articulation.

`CM022`–`CM026` certify phrase boundaries, roles, structural relations, phrase-local cadences, and answer-linked antecedent/consequent structure.

`CM027`–`CM032` certify the solver-native SATB layer: beat shape and soprano anchoring, ranges/order, spacing, complete triadic realization/root doubling, inner-voice parallel-perfect avoidance, and inner leading-tone resolution.

`CM033`–`CM036` certify the v2.5 harmonic-form layer: explicit chord kind/inversion metadata, complete seventh realization and inversion agreement, chordal-seventh downward resolution, and global dominant-seventh resolution.

v2.6 adds four tonicization rules:

- `CM037` — tonicization context: enabled artifacts carry one nullable target per beat; non-null targets are supported local diatonic tonics, use seventh form, and satisfy `minimum_applied_dominants`;
- `CM038` — applied-dominant realization: global root degree, target-derived dominant-seventh pitch-class set, completeness, and inversion/bass agreement are recomputed independently;
- `CM039` — target resolution: every applied dominant resolves immediately to its declared untargeted diatonic target chord;
- `CM040` — local tendency resolution: the applied chordal seventh moves down by step and the local leading tone moves up by semitone in whichever SATB voice carries each tone.

## Solver/verifier symmetry

Every hard musical consequence introduced by the solver has a separately implemented post-solve check. Configuration validation may reject malformed declarations before model construction, but certification never trusts that a CP-SAT constraint was present merely because the solver returned `OPTIMAL` or `FEASIBLE`.

For SATB and harmonic context, the verifier receives ordinary MIDI-note arrays, global chord degrees, chord-kind/inversion metadata, and nullable tonicization targets. It reconstructs pitch classes and target-derived applied-dominant identities itself.

A solver assignment that fails this independent pass raises `InternalVerificationError` and is not exported as verified output.

## Preserved outer-voice semantics

v2.6 deliberately does not reinterpret `CM005` or `CM006`.

- `CM005` still requires the strong-grid melody/soprano to belong to the global diatonic triad identified by `chord_degrees[beat]`.
- `CM006` still requires bass to belong to that same global diatonic triad.

Applied-dominant chromatic tones therefore occur in inner voices. A candidate tonicization target is exposed only when its applied dominant can be represented completely while preserving those historical outer-voice rules. Unsupported targets are rejected by the theory/configuration layer instead of being admitted through a verifier exception.

This boundary is important for artifact compatibility: v2.6 expands harmonic context without changing the meaning of any earlier rule ID.

## Applied-dominant verification

For a non-null target degree `t`, the verifier derives:

1. the target pitch class from the global key;
2. the applied-dominant root one perfect fifth above that target;
3. the dominant-seventh pitch classes `(root, major third, perfect fifth, minor seventh)`;
4. the expected global diatonic root degree stored in `chord_degrees`;
5. the bass pitch class implied by the serialized inversion.

It then requires the four SATB voices to realize those four pitch classes exactly once. The following beat must have `chord_degrees == t` and `tonicization_target == null`.

The local leading tone is the major third of the applied dominant and must move up one semitone. The applied chordal seventh must move down one or two semitones. These checks inspect all four voices independently.

## Search-objective verification

Optimization preferences remain outside the hard musical contract. The model exposes five minimized objective components:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

A separate application-level function reconstructs the same objective vector from finished musical values. Compiled and independently reconstructed vectors must agree exactly or generation fails closed.

No-good distinctness dimensions also remain search semantics rather than hard-rule semantics. v2.6 keeps the established meanings of `melody`, `rhythm`, `bass`, `harmony`, `voicing`, and `harmonic_form`, and adds `tonicization` for the nullable local-target sequence.

## Artifact integrity

A current v2.6 JSON artifact carries:

- artifact schema version `2.6`;
- constraint-contract version `2.6`;
- SHA-256 of the canonical `CM001`–`CM040` contract;
- SHA-256 of the semantic specification and musical result;
- SATB soprano/alto/tenor arrays;
- harmonic kind/inversion metadata when present;
- tonicization-target metadata when present;
- independently recomputable objective-vector metadata;
- SHA-256 of the complete serialized spec/solver/validation/music/search payload;
- IDs of the hard constraints checked at generation time.

The semantic composition digest commits tonicization targets, so changing a local target while leaving the notes untouched is detectable as provenance tampering. The full artifact digest additionally commits serialized validation/search metadata.

`constraint-music verify artifact.json` checks musical validity plus current provenance. `--allow-legacy` remains available when intentionally inspecting older artifacts whose schema/contract predates the current verifier.

## Historical payloads

SATB payloads that predate v2.5 may omit harmonic-form arrays. Payloads that predate v2.6 may omit tonicization targets. Constraint Music does not synthesize fictional metadata for those artifacts. Missing tonicization metadata is accepted only when the loaded specification has tonicization disabled; a current tonicization-enabled artifact must carry explicit target data and fails `CM037` otherwise.

## Claim boundary

Independent verification is an application-level separation of trust, not a formal proof of OR-Tools, Python, or the host machine. Constraint compliance demonstrates conformance to the declared executable contract; it does not prove aesthetic quality, perceptual optimality, or complete historical-style authenticity.

v2.6 implements bounded tonicization through applied dominant sevenths. It does not yet certify modal mixture, secondary leading-tone chords, persistent local-key regions, pivot-chord modulation, arbitrary chromatic harmony, or third-inversion sevenths. Pareto mode returns candidates nondominated within its explored pool; it does not prove enumeration of the global mathematical Pareto frontier.
