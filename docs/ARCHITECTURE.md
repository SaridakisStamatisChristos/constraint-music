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
       |   \-> beat-level SATB realization    |
       v                                       |
 feasible + optimized assignment               |
       |                                       |
       +--> no-good enumeration / scalarization|
       |                                       |
       v                                       |
ordinary Python musical values + SATB voices   |
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

v2.4 extends the same boundary to four-part harmony. Soprano, alto, tenor, and bass are solved inside CP-SAT, serialized as ordinary MIDI-note arrays, and then independently checked for SATB shape, ranges/order, spacing, complete triads/root doubling, inner-voice parallel perfects, and tendency-tone resolution. The verifier never queries SATB solver variables.

## Contract

`constraint_music.contract` defines stable IDs for every hard musical rule. The compiler and verifier are required to cover the same contract. This is enforced by tests and by adversarial mutations that target historically fragile rules.

The v2.4 contract contains `CM001`–`CM032`; the final six IDs are SATB-specific conditional rules. Search strategy is outside that hard-rule contract. No-good cuts restrict which already-valid assignment may be returned next; weighted scalarization ranks feasible assignments; Pareto filtering compares independently reconstructed objective vectors. None of these mechanisms may waive a `CM` rule.

## SATB compiler

The SATB harmonic skeleton operates at one sonority per beat. Soprano is an explicit beat-level variable constrained to equal the melody at each beat's strong grid step. Alto and tenor are independent solver variables, and bass reuses the existing beat-level bass variable.

Pitch-class variables are linked to each SATB voice with modulo constraints. A compact allowed-assignment table jointly constrains chord degree and four voice pitch classes, guaranteeing that all voices are chord members, all three triad pitch classes are present, and the root is doubled. Ordering/spacing use direct integer constraints. Inner-voice parallel-perfect and leading-tone rules are compiled as transition tables over adjacent beats.

## Optimization

All hard musical rules remain non-negotiable. The objective vector has five minimized components:

- tension deviation;
- melody motion;
- bass motion;
- harmonic repetition;
- contour mismatch.

SATB feasibility is deliberately not converted into a soft objective in v2.4. Seeded jitter is retained only as a deterministic tie-break within scalarized solves and is not a Pareto dimension.

## Distinct enumeration

Alternative generation uses exact no-good cuts over explicit dimensions (`melody`, `rhythm`, `bass`, `harmony`). Every previously accepted assignment contributes one cut requiring at least one selected variable to differ.

In v2.4, `harmony` includes chord degrees plus alto and tenor assignments, so alternative voicings can be enumerated without pretending that identical chord symbols are identical harmonic realizations.

## Pareto approximation

Pareto mode explores a deterministic family of weighted scalarizations, applies no-good cuts so candidates remain distinct, independently reconstructs each objective vector, and removes dominated candidates from the explored pool.

Because the pool is bounded, this is intentionally an approximation of the global Pareto frontier.

## Extension boundary

New hard musical rules should be introduced in four places as one change: contract metadata, solver compilation, independent verification, and adversarial tests. This prevents silent drift between the generator and verifier.

New search objectives should instead define their CP-SAT component, independent reconstruction formula, scalarization behavior, artifact metadata, and search-level tests without inventing a new hard-rule ID unless they genuinely change musical feasibility.
