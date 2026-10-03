# Distinct Enumeration and Pareto Search — v2.3

Constraint Music v2.3 separates two questions that earlier releases conflated:

1. Is a composition valid under the hard musical contract?
2. Which valid composition should the search return?

The first question is still answered exclusively by the independent `CM001`–`CM026` verifier. v2.3 changes the second question by making alternative enumeration and objective tradeoffs explicit.

## Distinct enumeration

`generate_many()` no longer changes the seed and hopes to obtain different outputs. After every accepted composition, the next CP-SAT model receives a no-good cut over the selected dimensions.

Supported distinctness dimensions are:

- `melody`
- `rhythm`
- `bass`
- `harmony`

A no-good cut requires at least one selected variable to differ from each previously accepted composition. For example, `distinct_on=("melody", "harmony")` guarantees that every returned candidate differs from each earlier candidate in at least one melody or harmony value.

Single-worker search with a fixed seed is deterministic, including enumeration order.

### CLI

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --count 4 \
  --distinct-on melody,harmony \
  --output build/period.mid \
  --json build/period.json
```

## Objective vector

The old scalar objective is decomposed into five named minimized components:

1. `tension_deviation` — absolute mismatch from the requested tension curve;
2. `melody_motion` — excess melodic leaps plus repeated-note pressure;
3. `bass_motion` — excess bass leaps;
4. `harmonic_repetition` — adjacent repeated chord degrees;
5. `contour_mismatch` — failure of strong-beat melodic direction to follow large tension-curve changes.

Random-seed jitter remains only as a deterministic tie-break inside a scalarized solve. It is not part of the Pareto vector.

For every accepted solve, the application independently reconstructs the objective vector from the serialized melody, bass, harmony, tension target, and specification. If that vector differs from the values produced inside CP-SAT, generation fails closed with `InternalVerificationError`.

JSON schema 2.3 stores this independently checkable objective vector in the `search.objective_vector` section. The artifact-content digest covers the search metadata, and offline verification rejects objective-vector tampering.

## Weighted scalarization

`generate_weighted()` accepts a mapping or sequence of objective weights. Missing mapping keys inherit the default weights. Every weight must be in `0..1000`, and at least one objective must have a positive weight.

The default scalarization preserves the intent of the previous v2.2 objective:

```text
tension_deviation     8
melody_motion         2
bass_motion           3
harmonic_repetition   1
contour_mismatch      4
```

Lower values are always better.

## Pareto-front approximation

`generate_pareto()` is deliberately described as an approximation rather than an exact multi-objective enumerator.

The algorithm:

1. derives a deterministic family of scalarization profiles from the default weights;
2. solves one distinct candidate per profile using the same hard musical contract;
3. independently computes each candidate's objective vector;
4. removes every candidate dominated by another candidate in the pool;
5. returns up to the requested number of nondominated candidates.

Candidate-pool size is bounded to keep runtime predictable. Therefore a returned set is nondominated within the explored pool, not proof of the complete mathematical Pareto frontier of the full feasible space.

### CLI

```bash
constraint-music generate examples/eight_bar_period.yaml \
  --pareto \
  --count 4 \
  --pareto-candidate-multiplier 3 \
  --distinct-on melody,harmony \
  --output build/pareto.mid \
  --json build/pareto.json
```

## Dominance

For objective vectors `A` and `B`, `A` dominates `B` exactly when:

- every component of `A` is less than or equal to the corresponding component of `B`; and
- at least one component of `A` is strictly smaller.

The dominance implementation is pure application logic and is tested independently from CP-SAT.

## Contract boundary

v2.3 introduces no new hard musical rule IDs. A candidate still has to satisfy `CM001`–`CM026` before it may participate in enumeration or Pareto ranking.

This separation is intentional:

```text
hard musical feasibility -> independent verification -> search/ranking metadata
```

Search strategy never upgrades an invalid composition into a valid one.
