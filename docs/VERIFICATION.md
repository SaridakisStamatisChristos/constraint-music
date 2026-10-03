# Verification model

Constraint Music v2.0a1 defines 16 hard rules (`CM001`–`CM016`). The verifier checks them from a serialized result plus its generation specification, without rerunning the solver.

The contract covers shape, pitch domains, harmony domain, chord membership, progression legality, melodic leap limits, tritone avoidance, leading-tone resolution, repetition bounds, large-leap recovery, bass leap/tritone limits, parallel-perfect avoidance, and authentic-cadence requirements.

## Why this changed from v1.1

The recovered v1.1 solver enforced melodic/bass tritone avoidance and large-leap recovery, but the separate validator did not re-check those rules. v2 closes that gap and makes failed rules explicit by ID.

## Artifact integrity

A v2 JSON artifact carries:

- artifact schema version;
- constraint-contract version;
- SHA-256 of the canonical contract;
- SHA-256 of the semantic specification + musical result;
- SHA-256 of the complete serialized spec/solver/validation/music payload;
- IDs of the constraints checked at generation time.

`constraint-music verify artifact.json` checks both musical validity and those integrity fields. `--allow-legacy` permits old JSON without v2 provenance to receive musical verification only.

## Claim boundary

This is independent application-level verification, not a formal proof that OR-Tools itself is correct and not proof of equivalence for every future implementation. The engineering claim is narrower: generated artifacts are re-evaluated by a separate code path against the declared hard-rule contract, and regression/adversarial tests are used to detect drift.
