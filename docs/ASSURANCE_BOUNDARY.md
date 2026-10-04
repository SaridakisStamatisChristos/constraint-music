# Assurance Boundary

## Strict claim

For an independently fixed request `C`, supported contract `H`, current artifact `x`,
and declared MIDI render profile `R`, the strict interface evaluates:

```text
verify_artifact(x, expected_spec=C, contract_version=H)
certify_delivery(x, midi, expected_spec=C, render_profile=R)
```

Acceptance requires all of the following:

1. exact current-schema object, type, null, enum, and array shape before reconstruction;
2. canonical equality with independently supplied `C`;
3. current contract version and digest;
4. a fresh semantic evaluation with no failed or blocked applicable rule;
5. exact equality between serialized claims and the fresh report;
6. recomputed objective, composition, request, and artifact-content digests;
7. exact ordered note-event and key-context equality after independent MIDI parse-back.

The compatibility `verify` command checks consistency under the embedded request. It
does not authenticate the original request. Copying `artifact.spec` into `--spec` does
not create independent trust.

## Render profiles

| Profile | Certified streams | Explicit exclusions |
|---|---|---|
| `certified-satb` | Conductor context plus exact beat-level S, A, T, B pitches/timing | Subdivision melody and arbitrary player behavior |
| `melody-plus-satb` | The SATB projection plus the independent rhythmic melody projection | A claim that five simultaneous streams form legal four-part harmony |
| `legacy-preview` | None; compatibility preview only | All delivery-certification claims |

Voice identity, MIDI pitch, onset, duration, channel, track identity, ticks per beat,
and declared key-change events are compared. Key signatures describe context; they do
not replace pitch checking.

## Non-claims

This release does not claim unique tonal inference from unlabeled MIDI, enharmonic
spelling correctness, unrestricted modulation, musical aesthetics, solver optimality,
authenticated authorship, universal tamper resistance, or global compiler/checker
equivalence. SHA-256 values bind data only relative to separately trusted expected
values; they are not signatures.

## Failure semantics

- strict accept: exit `0`;
- semantic, binding, integrity, or delivery rejection: exit `1`;
- malformed/unsupported input or execution failure: exit `2`.

Malformed prerequisites never become `NOT_APPLICABLE`; they are rejected at the shape
boundary or recorded as `BLOCKED` for direct in-memory verification.

