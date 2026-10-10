# Fresh paired study v2: frozen before heldout generation

## Question and primary outcome

For a request drawn from the grammar below, what is the probability that a
conditioned native engine produces a delivered, common-adapted MIDI satisfying
**every stated obligation in both scheduled runs**? The request is the unit of
analysis. The two runs are not independent observations and never double the
sample size. There are 128 primary requests, three engines and two runs: 768
primary attempts. Four deliberately unsupported requests add 24 admission slots,
outside the primary denominator. No output, timeout, rejected output, blocked
inspection or harness error counts as primary success. Unsupported requests are
reported separately, never as musical failures. An unresolved harness error
invalidates a superiority claim, even though it remains in the denominator.

The primary profile uses the identical declared MIDI renderer for every engine.
It only writes supplied pitches, voices, times and context. It does not search,
repair, or filter results. The independent check verifies the exact native score
to normalized-event mapping and the delivered-byte relation. Native export is
a separate secondary column, never pooled with adapted delivery. This experiment
compares conditioned engines with that renderer, not their unmodified product UX.

## Obligations and support

Each request is major in C/G/D/A/E/F/Bb/Eb, 8 or 12 consecutive quarter-note
chords, in 4/4 at 90/108/120/132 BPM. It states diatonic degrees, root/first/second
inversions, a fixed bass pitch on every chord, optional exact soprano anchors,
and complete triads or complete dominant sevenths. Dominant sevenths always
precede tonic. SATB ranges are S60..84, A55..74, T48..67, B48..59; strict ordering;
adjacent upper spacing at most 12 semitones; no same-direction parallel perfect
fifths or octaves between any pair. Every leading tone at V–I rises exactly one
semitone; every chordal seventh descends one or two semitones. Rests, ties, minor,
third inversions and other seventh qualities are outside this adapter contract.
“Unsupported” is about this declared profile, not a claim about all upstream
capabilities. The fixed bass puts music21's bass-input interface on equal terms
with the two constraint solvers. Every engine receives identical MIDI basses.

## Sampling and separation

`corpus.sample` fixes the entire sampling algorithm before heldout generation.
Development uses seed 20261009, eight draws. Heldout uses seed 20261011, 128 draws.
Each candidate independently chooses one of four eight-chord templates, optional
I–IV–V–I prefix, key, inversion per chord (first/last root), dominant-seventh flags
and tempo. A finite, engine-independent voicing/path search admits only requests
with a valid witness. Then zero/one/two soprano anchors are selected uniformly
from chord positions and assigned the witness pitches. The witness is retained
for feasibility evidence; **no generator worker receives it**. It chooses a low
lexicographic witness, so anchor-register bias is explicit. Rejection counts
are retained. No admission decision depends on any compared engine's output.

Draws are IID with replacement from this feasible conditional grammar; exact
duplicates are retained and counted, not replaced after seeing outcomes. The
unseen heldout requests have new identifiers and an independent sampling seed;
the harmonic templates are public and are not unseen families. The interval's
population is this grammar and these adapters/budgets. It is not a confidence
claim for all music, arbitrary prompts, listening quality, or production use.
The sample size is a fixed, modest study budget, not a promised power level.

## Engines, conditioning and fairness

Versions and budgets are in `manifest.json`. Fresh workers have the same 30-second
wall cap including import, compilation, search, export and rendering. CP-SAT and
Gecode also have 20-second native search caps. music21's finite movement-DAG
enumeration is covered by the wall cap; it has no equivalent internal search
timer. One search thread and numerical-library thread caps are used. Engine order
rotates by request. Seeds 7 and 19 vary CM's CP-SAT seed; music21 and Diatony are
deterministic and repeat their same selection. Timing is descriptive, includes
export, and is not a speed-superiority endpoint. Peak RSS is maximum process RSS,
not summed process-tree memory. Record wall time and status even for nonoutputs.

CM receives a quarter harmonic unit, fixed degree/kind/inversion/bass/soprano,
all allowed progression edges, and added all-voice cadential leading-tone posts.
It clears the objective and selects its first feasible solution. Its native
strict ranges, spacing, parallel and seventh rules remain. No source changes.

music21 receives explicitly diatonically **spelled** basses and figured-bass
inversion notation. Native single/pair rules receive the common ranges, strict
ordering, spacing, soprano anchors and resolutions before the movement DAG is
built. The native V7 special-resolution shortcut is disabled because it forces
an incomplete tonic; ordinary native possibility search supports the requested
complete chords. Hidden-perfect and overlap rules are disabled via native
configuration because the shared contract does not prohibit them. Its native
movement graph chooses the first complete viable path, with no oracle selection.

Diatony is clean pinned upstream with a capture subclass posting fixed bass,
soprano anchors, complete chords, common ranges/ordering/spacing and cadential
resolution before first-feasible native DFS. Original additional native musical
rules remain in every engine. Such extra rules can reduce task completion; their
effects are configuration-specific, not evidence of general musical inferiority.
No compared engine is supplied another engine's solution or the reference witness.

CM/music21 native MIDI has the requested quarter grid and context. Diatony's
unchanged native writer uses anonymous four-quarter chords without sufficient
voice/context identity. Its native full conformance is **UNOBSERVABLE**. The
adapted profile explicitly maps each native chord index to one quarter and
preserves each pitch and voice, then supplies declared key/meter/tempo. It retains
both the original native bytes and adapted bytes. This timing transformation is
an adaptation, not a native-export success.

## Paired inference and claim gate

For CM against each competitor, report all four paired binary counts, the
per-request signed pass difference and mean risk difference. Apply the exact
two-sided McNemar test: conditional on discordant pairs, wins are Binomial(m,1/2).
Zero discordance gives p=1. Two prespecified comparisons use Bonferroni p-values
and alpha .025 each.

The interval is a deliberately conservative paired construction. Let p10 and
p01 denote the two discordant-cell probabilities. Each has a binomial marginal
count over the same 128 paired requests. Form each two-sided Clopper–Pearson
interval at alpha/2, then subtract bounds: [L10−U01, U10−L01]. The union bound
gives at least 1−alpha coverage without assuming independence of the two cells.
Two intervals at 97.5% each give at least 95% simultaneous coverage for the two
comparisons. The implementation uses binomial inversion, with independently
verified numerical reference values. This is not an unpaired proportions test,
an ordinary Wald interval, or a bootstrap of duplicated run rows.

Declare superiority on this measured outcome and grammar only if **both**
comparison intervals have lower bounds strictly above +0.10, both exact p-values
are below .025, every primary output has independent-checker agreement, and no
harness error/block is unresolved. Otherwise report that superiority was not
established. Equal rates do not establish equivalence. No outcome-driven change
to requests, adapters, thresholds, budget, sample size or primary endpoint is
allowed after freezing. Improvements informed by heldout results require v3.

## Evidence and replay

Commit the development-validated source, then create and commit `freeze.json`
before generating heldout. The receipt hashes adapter/checker/sampler/statistics
code, native CM source, imported checking code, manifest and this protocol,
versions and Diatony binary. This is a repository freeze, **not external
preregistration or independent replication**. Retain all requests, return codes,
logs, native inputs/scores, native and adapted MIDI, normalized events and metrics.
Replay checks exact ZIP members/hashes, complete attempt slots, frozen sampling,
feasibility witnesses, native reconstruction, both semantic formulations,
independent SMF/mido parsing, request context, voiced bytes and computed analysis.

## References for interfaces and numerical validation

- [music21 figured-bass API](https://music21.org/music21docs/moduleReference/moduleFiguredBassRealizer.html)
- [SciPy exact binomial test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html)
- [SciPy Clopper–Pearson interval documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html)

The simultaneous paired interval above is an explicit marginal-interval/union-
bound derivation; SciPy is used as a numerical cross-check, not as its citation.
