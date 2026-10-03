# Verification model

Constraint Music v2.1 defines 21 hard rules (`CM001`–`CM021`). The verifier checks them from a serialized result plus its generation specification, without rerunning the solver.

`CM001`–`CM016` retain the v2.0 tonal/harmonic contract: shape, pitch domains, harmony domain, chord membership, progression legality, melodic leap limits, tritone avoidance, leading-tone resolution, repetition bounds, large-leap recovery, bass leap/tritone limits, parallel-perfect avoidance, and authentic-cadence requirements.

v2.1 adds a structural layer:

- `CM017` — rhythm state domain (`onset`, `tie`, `rest`);
- `CM018` — tie/rest grammar, tied-pitch identity, and run limits;
- `CM019` — per-bar onset/rest/tie density and optional downbeat onset;
- `CM020` — exact motif repetition/transposition including rhythm inheritance;
- `CM021` — newly articulated final tonic for authentic cadence.

## Solver/verifier symmetry

Every v2.1 hard rule has a CP-SAT-side enforcement path and a post-solve verifier path. A solver assignment that fails the verifier raises `InternalVerificationError` and is not exported as a verified composition.

## Artifact integrity

A v2.1 JSON artifact carries:

- artifact schema version;
- constraint-contract version;
- SHA-256 of the canonical contract;
- SHA-256 of the semantic specification + musical result, including rhythm;
- SHA-256 of the complete serialized spec/solver/validation/music payload;
- IDs of the constraints checked at generation time.

`constraint-music verify artifact.json` checks both musical validity and those integrity fields. `--allow-legacy` remains available for old artifacts without current provenance.

## Claim boundary

This is independent application-level verification, not a formal proof that OR-Tools itself is correct and not proof of equivalence for every future implementation. The engineering claim is narrower: generated artifacts are re-evaluated by a separate code path against the declared hard-rule contract, and regression/adversarial tests are used to detect drift.
