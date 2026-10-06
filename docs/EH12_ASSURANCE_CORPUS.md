# EH-12 consolidated assurance corpus

## Scope

PR-34 closes the six assurance residuals assigned to the consolidated corpus. The
versioned source is
[`eh12_assurance_manifest.json`](../research/configs/eh12_assurance_manifest.json),
the complete observations are retained in
[`eh12_assurance_raw.jsonl`](../research/results/eh12_assurance_raw.jsonl), and the
derived metrics are recorded in
[`eh12_assurance_summary.json`](../research/results/eh12_assurance_summary.json).

This is finite, deterministic assurance evidence. It does not establish population
robustness, universal musical soundness, or global compiler/checker equivalence.

## Evidence matrix

| Evidence family | Cases | Result |
| --- | ---: | --- |
| Frozen full-piece controls | 3 | 3 accepted |
| Pairwise interaction faults | 3 | 3 rejected by the declared rule and independent oracle |
| Current/legacy schema adversarial cases | 26 | 26 blocked before semantic reconstruction |
| Certified MIDI delivery controls | 4 | 4 exact parse-backs with SHA-256 output digests |
| Named compiler-clause deletions | 3 | 3 rejected; zero escapes across three phases |
| **Total** | **39** | **39 adjudicated; zero crashes or exclusions** |

The three frozen fixtures use distinct specifications and seeds. They cover modulation
with modal mixture, modulation with secondary harmony, and modal mixture with secondary
harmony. Their witness beats are disjoint. The third fixture includes rests and ties and
is certified under both `certified-satb` and `melody-plus-satb` delivery profiles.

The schema matrix covers all declared validator field families and every supported
legacy version (`2.12`) at the strict current-schema boundary. Raw rows retain stable case
and fixture IDs, attack clusters, expected and observed outcomes, issues, crash markers,
and exclusion markers.

The compiler experiment deletes one exact clause at a time:

- `CM057.root.beat-0.voice-2` from `secondary_seventh_satb`;
- `CM016.opening-tonic` from `harmony`;
- `CM018.initial-not-tie` from `rhythm`.

Each row retains the constraint index, registered phase span, forced witness, verifier
outcome, finalization outcome, and applicable independent-oracle result. Implementation
hashes bind the manifest, harness, oracles, compiler phases, delivery boundary, semantic
dispatch, and verifier.

## Reproduction

Use the pinned development environment and one-worker fixtures:

```bash
python -m research.eh12_assurance_corpus
git diff --exit-code -- research/results/eh12_assurance_raw.jsonl \
  research/results/eh12_assurance_summary.json
```

CI executes this replay on Python 3.11, 3.12, and 3.13. Any change to a fixture,
outcome, output digest, denominator, source hash, or summary makes the evidence-drift
gate fail.
