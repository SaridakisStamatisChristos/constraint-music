# EH-11 Performance Evaluation Method

EH-11 measures full-system cost, solution yield, verification overhead, memory, variance, and scaling without changing the musical contract or tuning the solver to improve benchmark appearance.

## Matrix

The controlled matrix is declared in `research/configs/eh11_performance_matrix.json`. It covers 1, 2, 4, 8, 16, and 32 bars with five fixed seeds across base SATB, rhythm/motifs, phrase grammar, expanded sevenths, applied harmony, secondary leading-tone seventh harmony, borrowed harmony, declared dominant-key modulation, and a supported borrowed-harmony/modulation combination.

Every matrix point is attempted with one worker for reproducibility and, when the runner exposes more than one logical CPU, a throughput condition capped at four workers. Structurally inapplicable size/profile combinations are recorded as explicit exclusions rather than silently omitted. A separate multi-output slice requests three distinct base-SATB solutions at 4, 8, and 16 bars for three fixed seeds under both worker conditions.

The per-case CP-SAT limit is two seconds. This intentionally creates observable yield boundaries at larger/harder configurations instead of allowing the benchmark to hide difficult cases behind unbounded solver time.

## Timing boundaries

For successful single-output cases the harness records generation total, CP model compilation, OR-Tools solver wall time, generation residual, fresh semantic verification, artifact construction, artifact JSON parse/shape validation, strict external-request artifact certification, semantic rechecks performed inside strict certification, the remaining integrity/request-binding cost, certified-SATB MIDI export, independent delivery parse-back/checking, absolute certification cost, and the certification-to-generation ratio.

`NoSolutionError` is not interpreted as proof of infeasibility. The embedded solver status is retained when available, with `UNKNOWN`, `INFEASIBLE`, model errors, other no-solution outcomes, crashes, and explicit exclusions reported separately. All runnable attempts remain in yield denominators.

## Memory and variance

Each case runs in a fresh subprocess, making the operating-system `ru_maxrss` high-water mark local to that case rather than cumulative across the matrix. Python allocation peak is also captured with `tracemalloc`; RSS is the primary whole-process memory measure because OR-Tools uses native allocations outside Python's allocator.

Rows are grouped by feature profile, size, and worker condition. Machine-readable summaries retain count, median, mean, min, max, sample standard deviation, coefficient of variation, p90, and p95. Upper quantiles are emitted only when a group has at least five observations. Attempt-latency and memory statistics include every runnable attempt; successful-generation and certification statistics are reported separately so timeout/UNKNOWN cases are not silently discarded.

## Environment and evidence

The dedicated workflow runs on `ubuntu-24.04` with Python 3.12 and the repository's pinned development dependencies. The environment manifest records the exact commit and dirty state, platform, CPU model, logical CPU count, memory, Python and dependency versions, GitHub runner metadata, seeds, worker settings, time limit, and complete matrix declaration. The GitHub-hosted runner is an ephemeral measurement environment, so results are evidence for the recorded run rather than a cross-machine performance guarantee.

The authoritative artifacts are:

- `research/results/eh11_performance_raw.jsonl`;
- `research/results/eh11_performance_summary.json`;
- `research/results/eh11_environment.json`;
- `docs/EH11_PERFORMANCE_RESULTS.md`.

The workflow recomputes the summary from raw rows and requires exact equality before persisting the evidence. Optimization work triggered by a measured bottleneck belongs in a separate PR so EH-11 remains an observational baseline.
