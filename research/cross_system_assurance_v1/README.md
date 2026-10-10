# Cross-system assurance: development feasibility v1

This tree implements **the first gate** in the cross-system handoff. It is a
feasibility study, not the proposed paired held-out benchmark. PR38 was already
merged at baseline `d9c211a25d2391532ff3d2f1953e39e42850fe9a`. PR37 and its archived
protocol, corpus, oracles, observations and denominators are unchanged.

## Contract and support

The development scope is four symbolic voices in C/G major, sixteen quarter
notes of duration, and native Standard MIDI delivery. Notes may be quarters or
whole notes in these probes. Native adapters retain additional system-specific
requirements: music21 and Diatony receive I–IV–V–I; Constraint Music receives its
own tonal-progression contract. **Those requests are not identical.** No paired
rates or cost comparisons may be derived from these observations.

`manifest.json` pins the three independent engines, inputs, time caps and planned
six development slots. `support.json` distinguishes supported, unsupported and
unknown properties of the inspected interfaces, including request mapping.
Music21's figured-bass generator is independent from Constraint Music; this is
not the predicate comparator in `research/external_comparators.py`. Diatony and
Harmoniser share the Diatony voicing engine, so counting both would not supply
two independent external voicing generators.

The prototype semantic inspector reconstructs scale membership, four voice
identities, contiguous positive durations, endpoint length and noncrossing from
returned events. It imports neither Constraint Music's verifier/theory nor
music21's checking routines. It is intentionally **not a full tonal oracle**:
triad completeness, harmony obligations, parallels and leading-tone resolution
are not certified here. No fault-detection performance is claimed.

`midi_probe.py` independently parses original SMF bytes, retaining track/channel,
pitch, rational onset/duration, division and key/meter/tempo. A second parser,
mido 1.3.3, must agree. SMF 0/1 PPQN only is supported. Velocity-zero note-on
means note-off; running status and repeated pitches are handled. Equal musical
time under different PPQN values is an explicitly declared equivalence. The
original division and bytes remain preserved. No inferred pitch ordering is
accepted as delivered voice identity. Unknown/unobservable never means pass.

## Reproduce the inspection

From the repository root, with the pinned Python dependencies installed:

```bash
python -m research.cross_system_assurance_v1.feasibility --check
python -m pytest tests/test_cross_system_feasibility.py
```

This reparses all six original MIDI files, recomputes inspections and the summary,
and checks hashes and planned slots. It does not regenerate the music, require
Gecode, or contact external services. Default repository CI also runs this check.

For an owner-authorized fresh development pilot, use a new versioned study tree;
the runner refuses to overwrite an existing observation archive. Clone
[the upstream Diatony repository](https://github.com/sprockeelsd/Diatony), checkout
`2b13446c117c02626659e819ff975fef4b5daec2`, and install Gecode 6.2.0 development
headers/libraries. Linux build:

```bash
python -m research.cross_system_assurance_v1.build_diatony /path/to/Diatony /tmp/diatony-probe
python -m research.cross_system_assurance_v1.feasibility --diatony-binary /tmp/diatony-probe
```

`--prefix /path/to/extracted/packages` supports unpacked Ubuntu development
packages without a system install. The build rejects a dirty checkout or wrong
commit. It compiles unmodified upstream sources, supplies the missing transitive
`chrono` include via a compiler option, and links a small input/capture harness.
Native MIDI uses upstream `writeSolToMIDIFile` unchanged. `return_solution` values
are preserved as a native text record. The harness captures the public `return_solution` API without optional diagnostics.
It leaves restart-control lifetimes to the short-lived process instead of deleting
the engine-owned cutoff twice; explicit duplicate cleanup caused the first
harness crash after export.

The observed build used GCC 13.3.0, Ubuntu Gecode packages 6.2.0-5.1build3,
Boost headers 1.83.0-2.1ubuntu3.2 and MPFR headers 4.2.1-1build1.1. Python/package
versions and the probe executable digest are in `observations.json`. Exact
compiler/package provenance is additional environment evidence, not a claim that
all toolchain binaries are reproducibly built. No external source or executable
is vendored in this tree.

`debug_attempts/v0/` retains all six initial harness slots and original file hashes,
including four harness crashes. `deviation.json` identifies the old code commit
and the two development corrections. These preliminary slots are separate from
the corrected pilot; no holdout was used or replaced. Git records the declaration
before each run, without a claim of externally timestamped preregistration.

## Rights and independent replay

The repository and this newly written evaluator remain under its proprietary
license. This owner-authorized execution does not grant third-party research-run
rights. Public source visibility does not grant replay permission. A written
research-run permission or an explicitly approved separate evaluator license is
still required before promising independent outside reproduction.

The installed music21 Python license is BSD-3-Clause; no music21 corpus was used.
The pinned Diatony top-level license is CC0-1.0. Its embedded midifile identifies
Craig Stuart Sapp; [upstream midifile](https://github.com/craigsapp/midifile)
provides BSD-2-Clause terms, and [Gecode](https://www.gecode.org/license) provides
MIT terms. The embedded midifile revision is not independently identified here;
its redistribution provenance remains a review item. This tree distributes
new harness/evaluator code and generated pilot evidence, not those dependency
sources or binaries. No license in the main repository was changed.

## Stop condition and next work

Read `FEASIBILITY_REPORT.md` for the derived gate and concrete missing capabilities.
A failed native-profile gate is not proof that no cross-system study is possible.
A separately declared instrumented renderer, another independent generator, or
a narrower descriptive comparison could change the scope. Instrumented delivery
must be labelled as **engine plus benchmark renderer** and evaluated separately
from original native delivery; assigning tracks/context after generation cannot
establish that the original export preserved them.

Until the two-external-system comparability gate passes, the handoff requires
keeping the bounded PR37 paper. No held-out corpus, large benchmark runner,
paired result tables, broader novelty claims or manuscript expansion are declared
complete by this feasibility change.

## GitHub transport of the original development history

The GitHub connector publishes a transport commit with the same tested files,
plus this transport note and a Git bundle. The original declaration, corrections
and six-pilot result commit `0dc982c86e0a2d8bfb2999cc4efa104936df1e65` are preserved
in `research/history/cross_system_feasibility_v1.bundle`, including source commits
mentioned by the development deviations. The bundle requires baseline
`d9c211a25d2391532ff3d2f1953e39e42850fe9a` and can be verified with
`git bundle verify research/history/cross_system_feasibility_v1.bundle`. CI restores
its original branch into `refs/assurance/cross-system-feasibility-v1-original`.
This preserves local collection history without asserting external preregistration.
