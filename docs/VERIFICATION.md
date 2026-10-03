# Verification model

Constraint Music v2.3 retains 26 hard musical rules (`CM001`–`CM026`). The verifier checks them from a serialized result plus its generation specification, without rerunning the solver.

`CM001`–`CM016` retain the v2 tonal/harmonic contract: shape, pitch domains, harmony domain, chord membership, progression legality, melodic leap limits, tritone avoidance, leading-tone resolution, repetition bounds, large-leap recovery, bass leap/tritone limits, parallel-perfect avoidance, and the backward-compatible whole-piece closure rule.

v2.1 adds the rhythm/motif layer:

- `CM017` — rhythm state domain (`onset`, `tie`, `rest`);
- `CM018` — tie/rest grammar, tied-pitch identity, and run limits;
- `CM019` — per-bar onset/rest/tie density and optional downbeat onset;
- `CM020` — exact motif repetition/transposition including rhythm inheritance;
- `CM021` — newly articulated final tonic for the legacy whole-piece closure.

v2.2 adds the phrase layer:

- `CM022` — phrase IDs/spans are unique, in bounds, and non-overlapping;
- `CM023` — phrase-role opening/closing semantics;
- `CM024` — exact repeat/transpose/answer/sequence reconstruction;
- `CM025` — exact phrase-local cadence semantics;
- `CM026` — answer-linked antecedent/consequent open-to-strong structure.

v2.3 adds no new hard musical IDs. Distinct enumeration and Pareto ranking operate only after the same feasible-set contract has been compiled.

## Solver/verifier symmetry

Every hard musical rule has both a CP-SAT-side enforcement path and a post-solve verifier path. Phrase metadata is validated before model construction, while every musical consequence of that metadata is compiled and then reconstructed independently by the verifier.

A solver assignment that fails the verifier raises `InternalVerificationError` and is not exported as a verified composition.

## Search-objective verification

v2.3 additionally makes the search objective auditable without promoting optimization preferences into hard musical rules.

The CP-SAT model exposes five minimized objective components:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

After each solve, a separate application-level function reconstructs the same objective vector directly from the finished melody, bass, harmony, tension target, and generation specification. If the compiled vector and independently reconstructed vector differ, generation fails closed with `InternalVerificationError`.

The objective-vector check is deliberately separate from `CM001`–`CM026`: a different objective value changes ranking, not musical validity.

## Phrase verification

The phrase verifier does not inspect CP-SAT variables or solver state. It reads only the finished `GenerationResult` and specification and reconstructs:

- phrase boundaries;
- role-specific harmonic openings/closures;
- source/target melodic and rhythmic relations;
- cadence chord sequences and tonic outer-voice endings;
- answer-linked antecedent/consequent strength ordering.

`repeat` and `transpose` compare complete equal-length phrase spans. `answer` compares the declared opening fragment. `sequence` reconstructs every target fragment from the source fragment and the declared per-copy semitone step.

## Artifact integrity

A v2.3 JSON artifact carries:

- artifact schema version;
- constraint-contract version;
- SHA-256 of the canonical hard-rule contract;
- SHA-256 of the semantic specification + musical result;
- integrity-protected `search.objective_vector` metadata;
- SHA-256 of the complete serialized spec/solver/validation/music/search payload;
- IDs of the constraints checked at generation time.

Offline verification independently recomputes the objective vector and rejects search-metadata tampering as well as ordinary composition/provenance tampering.

`constraint-music verify artifact.json` checks both musical validity and those integrity fields. `--allow-legacy` remains available for old artifacts without current provenance.

## Claim boundary

This is independent application-level verification, not a formal proof that OR-Tools itself is correct and not proof of equivalence for every future implementation. The engineering claim is narrower: generated artifacts are re-evaluated by separate code paths against the declared hard-rule contract and objective-vector semantics, and regression/adversarial tests are used to detect drift.

Constraint compliance is not a proof of aesthetic quality, perceptual optimality, or historical-style authenticity. Likewise, v2.3 Pareto mode returns candidates nondominated within its explored pool; it does not prove that the complete mathematical Pareto frontier of the feasible space has been enumerated.
