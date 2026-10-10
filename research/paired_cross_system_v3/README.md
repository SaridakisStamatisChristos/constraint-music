# Request-bound harmonization evaluation

See [PROTOCOL.md](PROTOCOL.md) for the committed prospective specification and
[API documentation](../../docs/REQUEST_BOUND_HARMONIZATION.md) for usage.

This study compares the new native request-bound API, the unmodified legacy CM
composition adapter, and unchanged v2 music21/Diatony configurations. The 128 v2
requests informed development and are retained as development replay, including
all 256 native scores and native/adapted MIDI deliveries. They are never called
a fresh holdout. The new heldout uses seed 20261013 only after source/receipt
commits. All systems receive the same requests, never feasibility witnesses.

```bash
python -m research.paired_cross_system_v3.runner development --binary /path/to/v2-diatony
# Commit validated source and development evidence.
python -m research.paired_cross_system_v3.runner freeze --binary /path/to/v2-diatony
# Commit freeze.json before generating heldout.
python -m research.paired_cross_system_v3.runner heldout --binary /path/to/v2-diatony
python -m research.paired_cross_system_v3.runner analyze
python -m research.paired_cross_system_v3.report
python -m research.check_paired_v3
```

The portable replay wrapper permits at most eight ULPs only for the conservative
confidence interval bounds; other values, types, membership and report text must
match exactly. No solver or comparator execution is needed for raw replay.

Pinned Diatony's capture binary is exactly the v2 binary; build with the unchanged
v2 build harness against clean pinned upstream and the declared Gecode prefix.
The evidence/code remains under the repository's existing proprietary license.
Reproduction commands do not grant an execution license or authorize external
redistribution. No release/tag, submission or independent replication is claimed.

## Completed outcomes

[REPORT.md](REPORT.md) derives all outcomes from the raw archive: new CM 128/128,
legacy CM 53/128, music21 111/128, adapted Diatony 38/128, with no timeouts, harness
errors or inspection blocks. All three exact paired comparisons are significant;
the +10-point practical improvement gate passes against legacy CM and Diatony,
but not music21. Counts from the old 128 development-replay requests are separate.
The manifest's `baseline_commit` retains v2's legacy source pin; `freeze.json`
identifies and hashes the actual new source, including the recursive native API.
The history bundle retains original source, receipt and collection commits so
CI can verify them even when publication uses a flattened GitHub commit.
