# Phrase Grammar — v2.2

Constraint Music v2.2 promotes phrase structure into the same explicit, verifiable layer already used for rhythm and motifs.

A phrase declaration lives inside `GenerationSpec`, so phrase identity and semantics are included in artifact provenance. The CP-SAT compiler enforces the musical consequences of the declaration, and the independent verifier reconstructs those consequences from the serialized result.

## Phrase spans

```yaml
phrases:
  - id: A
    start_bar: 0
    bars: 4
    role: antecedent
    cadence: dominant_open

  - id: B
    start_bar: 4
    bars: 4
    role: consequent
    cadence: dominant_to_tonic
    relation: answer
    source: A
    transpose_semitones: 7
    relation_steps: 4
```

Phrase IDs must be unique. Spans must stay inside the composition and may not overlap. Gaps are permitted.

## Roles

Supported roles are:

- `statement` — no additional role-specific hard rule;
- `antecedent` — opens on tonic and ends on dominant degree V;
- `consequent` — ends on an articulated tonic close;
- `transition` — no additional role-specific hard rule;
- `cadential` — ends on an articulated tonic close.

Roles are deliberately small and explicit. They are not claims that the engine has encoded every historical rule of phrase syntax.

## Cadence labels

v2.2 uses concrete symbolic cadence labels instead of treating every dominant-function closure as an undifferentiated “authentic cadence.”

- `none` — no phrase-local cadence rule;
- `tonic_close` — final chord I/i, tonic melody and bass, final melody state is `onset`;
- `dominant_open` — final chord V;
- `dominant_to_tonic` — penultimate chord V, final chord I/i, tonic outer voices, articulated final melody onset;
- `leading_tone_to_tonic` — penultimate chord vii°, final chord I/i, tonic outer voices, articulated final melody onset.

The older `require_authentic_cadence` configuration field remains supported for backward compatibility and is treated as a legacy whole-piece closure rule. New phrase-level work should prefer the precise labels above.

## Phrase relations

Supported relations are:

### `independent`

No source relation is imposed.

### `repeat`

The target phrase has the same length as the source and copies the complete source melody and rhythm exactly.

### `transpose`

The target phrase has the same length as the source, copies rhythm exactly, and sets every target melody pitch to `source + transpose_semitones`.

### `answer`

The opening fragment of the target reconstructs the opening fragment of the source. Rhythm is copied exactly and melody is shifted by `transpose_semitones`.

`relation_steps` selects the fragment length. If it is zero, one bar is used.

### `sequence`

A source opening fragment is repeated across the complete target phrase. Each copy uses:

```text
transpose_semitones + copy_index * sequence_step_semitones
```

Rhythm is inherited from the source fragment for every copy. `relation_steps=0` means one bar. The target span must be divisible by the selected fragment length.

## Antecedent/consequent period rule

When a phrase with role `consequent` uses relation `answer` and names an `antecedent` source, v2.2 additionally requires:

1. the antecedent opens on tonic;
2. the antecedent ends on V (`dominant_open` behavior);
3. the consequent recalls the declared source fragment;
4. the consequent ends with a tonic close;
5. the beat before the consequent close is V or vii°.

This is the executable meaning of `CM026`. It is intentionally a minimal period grammar, not a complete theory of classical periods.

## Contract rules

v2.2 adds:

- `CM022` — phrase-boundary integrity;
- `CM023` — phrase-role semantics;
- `CM024` — exact phrase-relation reconstruction;
- `CM025` — exact phrase-cadence semantics;
- `CM026` — answer-linked antecedent/consequent open-to-strong structure.

Every rule is independently checked after solving. A solver assignment that violates any phrase rule fails closed and is not exported as verified.

## Example

See `examples/eight_bar_period.yaml` for a two-phrase, eight-bar antecedent/consequent configuration.
