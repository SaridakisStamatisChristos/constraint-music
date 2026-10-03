# Architecture

Constraint Music is deliberately split into generation and verification paths.

```text
YAML GenerationSpec
       |
       v
  tonal theory/domain construction
       |
       v
CP-SAT compiler --------------------------+
       |                                   |
       v                                   |
 feasible + optimized assignment           |
       |                                   |
       v                                   |
independent verifier <--- hard contract ---+
       |
       +--> MIDI
       +--> verifiable JSON artifact
```

## Trust boundary

The CP-SAT model is not considered evidence that an output is correct. A generated assignment is converted into ordinary Python values and passed to `verify_result`. The verifier does not inspect OR-Tools variables, constraints, solver state, or proofs. If verification fails, generation fails closed with `InternalVerificationError`.

## Contract

`constraint_music.contract` defines stable IDs for every hard rule. The compiler and verifier are required to cover the same contract. This is enforced by tests and by adversarial mutations that target historically fragile rules.

## Optimization

All hard musical rules remain non-negotiable. The objective can trade among tension matching, melodic economy, bass economy, chord repetition, contour alignment, and seeded tie-breaking, but it cannot pay a penalty to violate a hard rule.

## Extension boundary

New musical rules should be introduced in four places as one change: contract metadata, solver compilation, independent verification, and adversarial tests. This prevents silent drift between the generator and verifier.
