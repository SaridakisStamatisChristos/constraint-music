# Architecture

Constraint Music is deliberately split into generation, search, and verification paths.

```text
YAML GenerationSpec
       |
       v
  tonal theory/domain construction
       |
       v
CP-SAT compiler ------------------------------+
       |                                       |
       v                                       |
 feasible + optimized assignment               |
       |                                       |
       +--> no-good enumeration / scalarization|
       |                                       |
       v                                       |
ordinary Python musical values                 |
       |                                       |
       +--> independent objective recomputation|
       |                                       |
       v                                       |
independent verifier <------- hard contract ---+
       |
       +--> MIDI
       +--> verifiable JSON artifact
```

## Trust boundary

The CP-SAT model is not considered evidence that an output is correct. A generated assignment is converted into ordinary Python values and passed to `verify_result`. The verifier does not inspect OR-Tools variables, constraints, solver state, or proofs. If verification fails, generation fails closed with `InternalVerificationError`.

v2.3 applies the same philosophy to optimization metadata. Objective-component values produced inside the model are independently reconstructed from ordinary musical values. A mismatch also fails closed.

## Contract

`constraint_music.contract` defines stable IDs for every hard musical rule. The compiler and verifier are required to cover the same contract. This is enforced by tests and by adversarial mutations that target historically fragile rules.

Search strategy is outside that hard-rule contract. No-good cuts restrict which already-valid assignment may be returned next; weighted scalarization ranks feasible assignments; Pareto filtering compares independently reconstructed objective vectors. None of these mechanisms may waive a `CM` rule.

## Optimization

All hard musical rules remain non-negotiable. The v2.3 objective vector has five minimized components:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

Seeded jitter is retained only as a deterministic tie-break within scalarized solves and is not a Pareto dimension.

## Distinct enumeration

Alternative generation uses exact no-good cuts over explicit dimensions (`melody`, `rhythm`, `bass`, `harmony`). Every previously accepted assignment contributes one cut requiring at least one selected variable to differ.

This makes distinctness a solver constraint rather than an accidental consequence of changing random seeds.

## Pareto approximation

Pareto mode explores a deterministic family of weighted scalarizations, applies no-good cuts so candidates remain distinct, independently reconstructs each objective vector, and removes dominated candidates from the explored pool.

Because the pool is bounded, this is intentionally an approximation of the global Pareto frontier.

## Extension boundary

New hard musical rules should be introduced in four places as one change: contract metadata, solver compilation, independent verification, and adversarial tests. This prevents silent drift between the generator and verifier.

New search objectives should instead define their CP-SAT component, independent reconstruction formula, scalarization behavior, artifact metadata, and search-level tests without inventing a new hard-rule ID unless they genuinely change musical feasibility.
