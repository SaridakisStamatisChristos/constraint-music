# Fair paired cross-system study v2

This new study preserves v1 and fixes its music21 enharmonic adapter error.
The [controlled diagnostic](DEVELOPMENT.md) reproduces the frozen wrong chord;
changing only G♯ to A♭ at the same bass MIDI pitch fixes it. This error is not
evidence against music21. Both diagnostic variants and original v1 bytes remain.

The [frozen protocol](PROTOCOL.md) declares 128 independently drawn feasible
requests with inversions, dominant sevenths and soprano anchors. Its primary
endpoint is conforming common-adapted MIDI in **both** scheduled runs; the request,
not each run or note, is the statistical unit. Native export is a separate
secondary profile. Four unsupported requests remain outside the denominator.
The [derived report](REPORT.md) and [request-level summary](summary.json) provide
paired differences, conservative simultaneous confidence intervals, exact
McNemar tests, the predefined +10 percentage-point gate, and limitations.

No engine receives the independent feasibility witness. No heldout result is
used to repair an output or change the adapter. All requests, failures, native
inputs/scores, original MIDI, normalized events, adapted MIDI and logs are retained.
The two deterministic repeat profiles do not constitute outside replication.

## Inspect and replay

The unchanged [license](../../LICENSE) requires written owner permission for
outside execution; use the [case-by-case route](../../docs/RESEARCH_REPLAY_PERMISSION_TEMPLATE.md).
No public execution grant, outside evaluator contact or license amendment is issued.

After permission, from the repository root:

```bash
python -m pip install -e . mido==1.3.3
git fetch --no-tags research/history/paired_cross_system_v2.bundle \
  refs/heads/research/fair-paired-cross-system-v2:refs/assurance/paired-cross-system-v2-original
python -m research.check_paired_v2
```

Replay needs only the checker dependencies, original protocol Git objects and
archives. It does not rerun generators or need Gecode/music21/OR-Tools. Source
commit `6ffa3f6` and freeze-receipt commit `a1cdd15` precede heldout generation.
The history bundle preserves those objects when GitHub transport flattens commits.
The original binary is hashed but is not redistributed.

The wrapper outside the frozen study permits at most eight floating-point ULPs
on the two computed confidence bounds. Python 3.11 reproduced one bound as
0.12704383281166098 rather than 0.1270438328116611. Every other value, type,
count, verdict, archive hash and rendered report remains exact. The original
study code, receipt and stored values are unchanged; this is portable replay,
not a new analysis or a changed superiority threshold.

Direct file inspection needs no repository execution:

```bash
python -m zipfile -l research/paired_cross_system_v2/heldout/evidence.zip
python -m json.tool research/paired_cross_system_v2/summary.json
```

Archives use `<request-id>.<system>.<seed>/<filename>`. `attempts.json` records
all 792 planned slots and exact files/hashes; `index.json` seals all three phase
files. `corpus.json` retains reference witnesses and rejection counts. They are
evidence for input feasibility, never supplied as native generator input.

## Generate a subsequent version

Do not overwrite this frozen study. Declare a fresh version and independent
sampling seed before outcomes, then run development, commit validated source,
freeze, commit the receipt, generate heldout, derive analysis and verify archives.
Generation uses the versions in [manifest.json](manifest.json), clean pinned
[Diatony](https://github.com/sprockeelsd/Diatony), Gecode 6.2.0 and C++11:

```bash
python -m pip install -e '.[dev]' mido==1.3.3
python -m research.paired_cross_system_v2.build \
  /path/to/clean/diatony /path/to/new-probe /path/to/gecode-prefix
```

Build-prefix layout is `usr/include` and `usr/lib/x86_64-linux-gnu`. The native
model is not edited or vendored. All engines retain extra native musical rules;
measured differences apply to these conditioned configurations and the declared
feasible grammar. A superiority claim requires the prespecified statistical and
practical gate, not a favorable raw percentage alone.
