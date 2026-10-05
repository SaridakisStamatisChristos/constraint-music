# EH-10 internal ablations and external comparators

## Purpose and safety boundary

EH-10 measures which assurance channels contribute detection signals on the frozen
EH-09 corpus and compares two narrow musical predicates with a pinned external
implementation. It does not add a production option to disable validation. Production
certification remains fail-closed and always executes its required checks.

The ablation is an observational, leave-one-channel-out union over recorded signals:

- `wire_shape`: current-schema structural admission;
- `semantic_rules`: fresh executable-contract verification;
- `integrity_request`: digests, claims, fresh-validation reconciliation, and the
  independently supplied request;
- `delivery_parseback`: independent MIDI projection parsing and comparison.

These channels overlap by design. In particular, integrity verification performs fresh
semantic verification when reconciling the serialized validation report. The reported
losses therefore describe this finite corpus, not causal effects, independent defenses,
or safe production configurations.

## Internal ablation result

The checked-in run contains 30 attacks and two valid controls. The union detects 30/30
attacks and flags 0/2 controls. Removing each channel from the observational signal
union produces:

| Omitted channel | Detected / 30 | Unique catches lost | Coverage |
| --- | ---: | ---: | ---: |
| Wire shape | 24 | 6 | 80.0000% |
| Semantic rules | 25 | 5 | 83.3333% |
| Integrity/request | 23 | 7 | 76.6667% |
| Delivery parse-back | 24 | 6 | 80.0000% |

Raw per-case statuses, reasons, applicable/blocked states, detected-by sets, production
outcomes, exact escape IDs, and implementation hashes are retained in
`research/results/assurance_ablation_rows.jsonl` and
`research/results/assurance_ablation_summary.json`.

## Pinned external adapters

The optional `comparators` extra pins `music21==9.9.2`, corresponding to upstream tag
`v9.9.2` and release commit `aa9780a` (BSD-3-Clause). The evidence generator rejects any
other observed version.

Two versioned adapters compare only shared, declared scopes:

| Adapter | Shared scope | Cases | Disagreements |
| --- | --- | ---: | ---: |
| `music21-voice-leading-v1` | Ordered two-voice, similar-motion parallel perfect fifth/octave predicate on a bounded MIDI/span/motion grid | 9,840 | 0 |
| `music21-c-major-triad-v1` | Four-note C-major diatonic triad completeness, root doubling, quality, and declared inversion under bounded valid/fault cases | 126 | 0 |

The voice-leading adapter normalizes enharmonic spelling because Constraint Music's
predicate is pitch-class based while music21 evaluates written interval quality. The
triad adapter requires the expected diatonic quality because music21's generic triad
classification also recognizes augmented triads. These transformations are explicit
scope alignment, not post-hoc case deletion; every generated case remains in the
denominator.

Excluded from comparison are whole-piece generation or quality, the complete SATB
contract, schema validation, provenance, request binding, delivery, contextual harmony,
rhythm, motifs, phrases, and modulation. Zero disagreements on these finite shared
scopes is not evidence that either complete system is equivalent or superior.

## Reproduction

```bash
python -m pip install -e ".[dev]"
python -m research.generate_eh10_evidence
git diff --exit-code -- research/results
```

CI runs the same regeneration on Python 3.11, 3.12, and 3.13. Tests verify the exact
dependency pin, denominators, results, and checked-in JSON replay.
