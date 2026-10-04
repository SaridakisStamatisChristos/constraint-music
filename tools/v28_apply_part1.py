from pathlib import Path
from textwrap import dedent

ROOT = Path('.')

def replace(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'missing replacement anchor in {path}: {old[:80]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

(ROOT / 'src/constraint_music/modulation.py').write_text(dedent('''
from __future__ import annotations

from .theory import PC_TO_SHARP_NAME, Key


def dominant_key(source: Key) -> Key:
    """Return the same-mode dominant key used by the bounded v2.8 modulation contract."""
    tonic_pc = source.pitch_classes[4]
    return Key(PC_TO_SHARP_NAME[tonic_pc], source.mode)


def common_tonic_pivot_destination_degree(source: Key, destination: Key) -> int:
    """Return the destination degree sharing the source-tonic triad, or raise."""
    source_pcs = set(source.triad_pitch_classes(0))
    matches = [
        degree for degree in range(7)
        if set(destination.triad_pitch_classes(degree)) == source_pcs
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one common destination triad for source tonic {source}; got {matches}"
        )
    return matches[0]
''').lstrip(), encoding='utf-8')

(ROOT / 'src/constraint_music/modulation_verify.py').write_text(dedent('''
from __future__ import annotations

from .modal_mixture import borrowed_triad_pitch_classes, canonical_modal_source
from .models import GenerationResult, RhythmState
from .modulation import common_tonic_pivot_destination_degree, dominant_key
from .satb import SatbGenerationResult
from .theory import ChordKind


def modulation_verification_issues(result: GenerationResult) -> tuple[tuple[str, str], ...]:
    spec = result.spec
    if not isinstance(result, SatbGenerationResult):
        if spec.modulation_enabled:
            return (("CM043", "Enabled modulation requires SATB key-context metadata"),)
        return ()

    issues: list[tuple[str, str]] = []
    contexts = result.key_contexts
    if not spec.modulation_enabled:
        if contexts:
            issues.append(("CM043", "Key-context metadata is present while modulation is disabled"))
        return tuple(issues)

    destination = spec.modulation_destination
    boundary = spec.modulation_boundary_beat
    if destination is None or boundary is None:
        issues.append(("CM044", "Enabled modulation lacks destination or boundary identity"))
        return tuple(issues)

    expected_destination = dominant_key(spec.tonal_key)
    if destination != expected_destination:
        issues.append(
            (
                "CM044",
                f"Destination {destination} is not the bounded dominant key {expected_destination}",
            )
        )
    if not 2 <= boundary <= spec.total_beats - 2:
        issues.append(("CM044", f"Modulation boundary {boundary} is outside the certified range"))
        return tuple(issues)

    if len(contexts) != spec.total_beats:
        issues.append(("CM043", "Key-context metadata must contain one key per beat"))
        return tuple(issues)

    expected_contexts = spec.expected_key_contexts
    if contexts != expected_contexts:
        issues.append(("CM048", "Serialized key-context sequence disagrees with the declared boundary"))

    pivot = boundary - 1
    pivot_degree = None
    try:
        pivot_degree = common_tonic_pivot_destination_degree(spec.tonal_key, destination)
    except ValueError as exc:
        issues.append(("CM045", str(exc)))
    if pivot < len(result.chord_degrees) and result.chord_degrees[pivot] != 0:
        issues.append(("CM045", "The certified pivot must be source tonic (degree 0)"))
    if pivot_degree != 3:
        issues.append(("CM045", "The bounded dominant-key pivot must reinterpret source I as destination IV"))
    if result.chord_kinds and result.chord_kinds[pivot] is not ChordKind.TRIAD:
        issues.append(("CM045", "The modulation pivot must remain triadic"))
    if result.tonicization_targets and result.tonicization_targets[pivot] is not None:
        issues.append(("CM045", "The modulation pivot cannot be tonicized"))
    if result.modal_sources and result.modal_sources[pivot] is not None:
        issues.append(("CM045", "The modulation pivot cannot be modally borrowed"))
    if all(len(v) == spec.total_beats for v in (result.soprano, result.alto, result.tenor, result.bass)):
        pivot_pcs = {
            result.soprano[pivot] % 12,
            result.alto[pivot] % 12,
            result.tenor[pivot] % 12,
            result.bass[pivot] % 12,
        }
        source_pcs = set(spec.tonal_key.triad_pitch_classes(0))
        dest_pcs = set(destination.triad_pitch_classes(3))
        if pivot_pcs != source_pcs or pivot_pcs != dest_pcs:
            issues.append(("CM045", "Pivot realization is not the exact common source-I/destination-IV triad"))

    kinds = result.chord_kinds
    targets = result.tonicization_targets or (None,) * spec.total_beats
    sources = result.modal_sources or (None,) * spec.total_beats
    if (
        len(kinds) == len(result.chord_inversions) == len(targets) == len(sources) == spec.total_beats
        and all(len(v) == spec.total_beats for v in (result.soprano, result.alto, result.tenor, result.bass))
    ):
        for beat in range(boundary, spec.total_beats):
            degree = result.chord_degrees[beat]
            if not 0 <= degree <= 6:
                continue
            key = destination
            pcs = {
                result.soprano[beat] % 12,
                result.alto[beat] % 12,
                result.tenor[beat] % 12,
                result.bass[beat] % 12,
            }
            kind = ChordKind.parse(kinds[beat])
            target = targets[beat]
            source = sources[beat]
            if target is not None:
                if target not in key.applied_dominant_targets:
                    issues.append(("CM046", f"Beat {beat}: tonicization target is invalid in destination key"))
                    continue
                expected = set(key.applied_dominant_seventh_pitch_classes(target))
            elif source is not None:
                if source is not canonical_modal_source(key):
                    issues.append(("CM046", f"Beat {beat}: modal source is stale for destination context"))
                    continue
                expected = set(borrowed_triad_pitch_classes(key, degree, source))
            elif kind is ChordKind.TRIAD:
                expected = set(key.triad_pitch_classes(degree))
            else:
                expected = set(key.seventh_pitch_classes(degree))
            if pcs != expected:
                issues.append(("CM046", f"Beat {beat}: harmony is not realized in destination-key context"))

    if len(result.chord_degrees) >= 2 and tuple(result.chord_degrees[-2:]) != (4, 0):
        issues.append(("CM047", "Destination region must close with V-I"))
    if contexts[-2:] != (destination, destination):
        issues.append(("CM047", "Destination cadence is not inside the destination key context"))
    if result.soprano and result.soprano[-1] % 12 != destination.tonic_pc:
        issues.append(("CM047", "Final soprano is not destination tonic"))
    if result.bass and result.bass[-1] % 12 != destination.tonic_pc:
        issues.append(("CM047", "Final bass is not destination tonic"))
    if result.tonicization_targets and any(x is not None for x in result.tonicization_targets[-2:]):
        issues.append(("CM047", "Destination cadence cannot be relabeled as tonicization"))
    if result.modal_sources and any(x is not None for x in result.modal_sources[-2:]):
        issues.append(("CM047", "Destination cadence cannot be modally borrowed"))
    if result.effective_rhythm and result.effective_rhythm[-1] is not RhythmState.ONSET:
        issues.append(("CM047", "Destination tonic must be a newly articulated final onset"))
    return tuple(issues)
''').lstrip(), encoding='utf-8')

replace('src/constraint_music/models.py',
'''from .modal_mixture import supported_borrowed_degrees\nfrom .phrase import PhraseSpec, normalize_phrases, phrase_by_id\nfrom .theory import DEFAULT_PROGRESSION_GRAPH_ROWS, Key, Mode, midi_note_name\n''',
'''from .modal_mixture import supported_borrowed_degrees\nfrom .modulation import dominant_key\nfrom .phrase import PhraseSpec, normalize_phrases, phrase_by_id\nfrom .theory import DEFAULT_PROGRESSION_GRAPH_ROWS, Key, Mode, midi_note_name\n''')
replace('src/constraint_music/models.py',
'''    modal_mixture_enabled: bool = False\n    minimum_borrowed_chords: int = 0\n\n    rhythm_enabled: bool = False\n''',
'''    modal_mixture_enabled: bool = False\n    minimum_borrowed_chords: int = 0\n\n    # v2.8 introduces one explicit, persistent same-mode modulation to the dominant key.\n    modulation_enabled: bool = False\n    modulation_destination_key: str | None = None\n    modulation_boundary_beat: int | None = None\n\n    rhythm_enabled: bool = False\n''')
replace('src/constraint_music/models.py',
'''        object.__setattr__(\n            self, "harmony_vocabulary", str(self.harmony_vocabulary).strip().lower()\n        )\n        object.__setattr__(self, "motif_relation", str(self.motif_relation).strip().lower())\n''',
'''        object.__setattr__(\n            self, "harmony_vocabulary", str(self.harmony_vocabulary).strip().lower()\n        )\n        if self.modulation_destination_key is not None:\n            normalized_destination = Key(str(self.modulation_destination_key), self.mode).tonic\n            object.__setattr__(self, "modulation_destination_key", normalized_destination)\n        object.__setattr__(self, "motif_relation", str(self.motif_relation).strip().lower())\n''')
replace('src/constraint_music/models.py',
'''    @property\n    def expanded_harmony_enabled(self) -> bool:\n        return self.harmony_vocabulary == "triads+sevenths"\n\n    @property\n    def progression_pairs(self) -> tuple[tuple[int, int], ...]:\n''',
'''    @property\n    def expanded_harmony_enabled(self) -> bool:\n        return self.harmony_vocabulary == "triads+sevenths"\n\n    @property\n    def modulation_destination(self) -> Key | None:\n        if not self.modulation_enabled or self.modulation_destination_key is None:\n            return None\n        return Key(self.modulation_destination_key, self.mode)\n\n    def active_key_at_beat(self, beat: int) -> Key:\n        if not 0 <= beat < self.total_beats:\n            raise IndexError(f"Beat {beat} is outside 0..{self.total_beats - 1}")\n        boundary = self.modulation_boundary_beat\n        destination = self.modulation_destination\n        if not self.modulation_enabled or boundary is None or destination is None or beat < boundary:\n            return self.tonal_key\n        return destination\n\n    @property\n    def expected_key_contexts(self) -> tuple[Key, ...]:\n        return tuple(self.active_key_at_beat(beat) for beat in range(self.total_beats))\n\n    @property\n    def context_keys(self) -> tuple[Key, ...]:\n        keys = [self.tonal_key]\n        destination = self.modulation_destination\n        if destination is not None and destination not in keys:\n            keys.append(destination)\n        return tuple(keys)\n\n    @property\n    def progression_pairs(self) -> tuple[tuple[int, int], ...]:\n''')
replace('src/constraint_music/models.py',
'''        if self.harmony_vocabulary not in {"triads", "triads+sevenths"}:\n            raise ValueError("harmony_vocabulary must be 'triads' or 'triads+sevenths'")\n''',
'''        if self.harmony_vocabulary not in {"triads", "triads+sevenths"}:\n            raise ValueError("harmony_vocabulary must be 'triads' or 'triads+sevenths'")\n        if self.modulation_enabled:\n            if self.require_authentic_cadence:\n                raise ValueError(\n                    "modulation_enabled requires require_authentic_cadence=false because CM016 "\n                    "remains the legacy global-key closure rule"\n                )\n            destination = self.modulation_destination\n            boundary = self.modulation_boundary_beat\n            if destination is None:\n                raise ValueError("modulation_enabled requires modulation_destination_key")\n            if boundary is None:\n                raise ValueError("modulation_enabled requires modulation_boundary_beat")\n            expected_destination = dominant_key(self.tonal_key)\n            if destination != expected_destination:\n                raise ValueError(\n                    f"v2.8 modulation_destination_key must be the same-mode dominant key "\n                    f"{expected_destination.tonic}"\n                )\n            _between("modulation_boundary_beat", boundary, 2, self.total_beats - 2)\n            if self.phrases:\n                raise ValueError(\n                    "v2.8 modulation does not yet compose with explicit phrase grammar; "\n                    "leave phrases empty"\n                )\n        elif self.modulation_destination_key is not None or self.modulation_boundary_beat is not None:\n            raise ValueError(\n                "modulation_destination_key/modulation_boundary_beat require modulation_enabled=true"\n            )\n''')
replace('src/constraint_music/models.py',
'''        if self.tonicization_enabled and self.minimum_applied_dominants > self.total_beats - 1:\n            raise ValueError(\n                "minimum_applied_dominants cannot include the final beat because tonicizations "\n                "must resolve"\n            )\n\n        _between(\n''',
'''        maximum_applied = self.total_beats - (4 if self.modulation_enabled else 1)\n        if self.tonicization_enabled and self.minimum_applied_dominants > max(0, maximum_applied):\n            raise ValueError(\n                "minimum_applied_dominants exceeds beats available outside required closure/context anchors"\n            )\n\n        _between(\n''')
replace('src/constraint_music/models.py',
'''        reserved_cadence_beats = 2 if self.require_authentic_cadence else 1\n        maximum_borrowed = max(0, self.total_beats - reserved_cadence_beats)\n''',
'''        reserved_cadence_beats = 4 if self.modulation_enabled else (2 if self.require_authentic_cadence else 1)\n        maximum_borrowed = max(0, self.total_beats - reserved_cadence_beats)\n''')
replace('src/constraint_music/models.py',
'''        _ = self.tonal_key\n        if self.tonicization_enabled and not self.tonal_key.applied_dominant_targets:\n            raise ValueError(\n                "The selected key has no applied-dominant targets compatible with the current "\n                "outer-voice contract"\n            )\n        if self.modal_mixture_enabled and not supported_borrowed_degrees(self.tonal_key):\n            raise ValueError(\n                "The selected key has no borrowed triads compatible with the current "\n                "outer-voice contract"\n            )\n''',
'''        _ = self.tonal_key\n        if self.tonicization_enabled:\n            for context_key in self.context_keys:\n                if not context_key.applied_dominant_targets:\n                    raise ValueError(\n                        f"Key context {context_key} has no applied-dominant targets compatible "\n                        "with the current outer-voice contract"\n                    )\n        if self.modal_mixture_enabled:\n            for context_key in self.context_keys:\n                if not supported_borrowed_degrees(context_key):\n                    raise ValueError(\n                        f"Key context {context_key} has no borrowed triads compatible with the "\n                        "current outer-voice contract"\n                    )\n''')

# Replace the tonal harmony compiler with an active-key-aware implementation.
p = ROOT / 'src/constraint_music/compiler_tonal.py'
text = p.read_text(encoding='utf-8')
start = text.index('def add_harmony_constraints(')
end = text.index('\ndef add_melodic_constraints(', start)
new_func = dedent('''
def add_harmony_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_choice: list[cp_model.IntVar],
    bass_choice: list[cp_model.IntVar],
    melody_domain: tuple[int, ...],
    bass_domain: tuple[int, ...],
) -> None:
    for left, right in pairwise(chord):
        model.add_allowed_assignments([left, right], spec.progression_pairs)

    for beat in range(spec.total_beats):
        key = spec.active_key_at_beat(beat)
        chord_melody_pairs = [
            (degree, note_index)
            for degree in range(7)
            for note_index, note in enumerate(melody_domain)
            if note % 12 in key.triad_pitch_classes(degree)
        ]
        chord_bass_pairs = [
            (degree, note_index)
            for degree in range(7)
            for note_index, note in enumerate(bass_domain)
            if note % 12 in key.triad_pitch_classes(degree)
        ]
        strong_step = beat * spec.subdivisions_per_beat
        model.add_allowed_assignments(
            [chord[beat], melody_choice[strong_step]], chord_melody_pairs
        )
        model.add_allowed_assignments([chord[beat], bass_choice[beat]], chord_bass_pairs)

    if spec.require_authentic_cadence:
        key = spec.tonal_key
        tonic_melody_indices = [
            i for i, note in enumerate(melody_domain) if note % 12 == key.tonic_pc
        ]
        tonic_bass_indices = [
            i for i, note in enumerate(bass_domain) if note % 12 == key.tonic_pc
        ]
        model.add(chord[0] == 0)
        model.add_allowed_assignments([chord[-2]], [(4,), (6,)])
        model.add(chord[-1] == 0)
        model.add_allowed_assignments([melody_choice[-1]], [(i,) for i in tonic_melody_indices])
        model.add_allowed_assignments([bass_choice[-1]], [(i,) for i in tonic_bass_indices])

    if spec.modulation_enabled:
        destination = spec.modulation_destination
        boundary = spec.modulation_boundary_beat
        if destination is None or boundary is None:
            raise ValueError("Validated modulation spec lost destination/boundary")
        pivot = boundary - 1
        tonic_melody_indices = [
            i for i, note in enumerate(melody_domain) if note % 12 == destination.tonic_pc
        ]
        tonic_bass_indices = [
            i for i, note in enumerate(bass_domain) if note % 12 == destination.tonic_pc
        ]
        model.add(chord[0] == 0)
        model.add(chord[pivot] == 0)
        model.add(chord[-2] == 4)
        model.add(chord[-1] == 0)
        final_strong = (spec.total_beats - 1) * spec.subdivisions_per_beat
        model.add_allowed_assignments(
            [melody_choice[final_strong]], [(i,) for i in tonic_melody_indices]
        )
        model.add_allowed_assignments([melody_choice[-1]], [(i,) for i in tonic_melody_indices])
        model.add_allowed_assignments([bass_choice[-1]], [(i,) for i in tonic_bass_indices])
''').lstrip('\n')
p.write_text(text[:start] + new_func + text[end+1:], encoding='utf-8')

# Core verifier: CM005/CM006 follow active local key only in the versioned modulation mode.
replace('src/constraint_music/verifier.py',
'''from .models import GenerationResult, RhythmState, ValidationReport\nfrom .phrase_verify import phrase_verification_issues\n''',
'''from .models import GenerationResult, RhythmState, ValidationReport\nfrom .modulation_verify import modulation_verification_issues\nfrom .phrase_verify import phrase_verification_issues\n''')
replace('src/constraint_music/verifier.py',
'''        strong_step = beat * spec.subdivisions_per_beat\n        if strong_step < len(melody):\n            strong_note = melody[strong_step]\n            if strong_note % 12 not in key.triad_pitch_classes(chord):\n                fail("CM005", f"Beat {beat}: strong melody note is not in {key.chord_name(chord)}")\n        if beat < len(bass) and bass[beat] % 12 not in key.triad_pitch_classes(chord):\n            fail("CM006", f"Bass beat {beat}: note {bass[beat]} is not in {key.chord_name(chord)}")\n''',
'''        active_key = spec.active_key_at_beat(beat)\n        strong_step = beat * spec.subdivisions_per_beat\n        if strong_step < len(melody):\n            strong_note = melody[strong_step]\n            if strong_note % 12 not in active_key.triad_pitch_classes(chord):\n                fail(\n                    "CM005",\n                    f"Beat {beat}: strong melody note is not in active-key "\n                    f"{active_key.chord_name(chord)}",\n                )\n        if beat < len(bass) and bass[beat] % 12 not in active_key.triad_pitch_classes(chord):\n            fail(\n                "CM006",\n                f"Bass beat {beat}: note {bass[beat]} is not in active-key "\n                f"{active_key.chord_name(chord)}",\n            )\n''')
replace('src/constraint_music/verifier.py',
'''    for rule_id, message in satb_verification_issues(result):\n        fail(rule_id, message)\n\n    return ValidationReport(\n''',
'''    for rule_id, message in satb_verification_issues(result):\n        fail(rule_id, message)\n    for rule_id, message in modulation_verification_issues(result):\n        fail(rule_id, message)\n\n    return ValidationReport(\n''')

# Contract v2.8 + explicit rule family.
replace('src/constraint_music/contract.py', 'CONTRACT_VERSION = "2.7"', 'CONTRACT_VERSION = "2.8"')
replace('src/constraint_music/contract.py',
'''        "strong_beat_chord_tone",\n        "Every strong-beat melody pitch belongs to the active triad.",\n''',
'''        "strong_beat_chord_tone",\n        "Every strong-beat melody pitch belongs to the active local-key triad.",\n''')
replace('src/constraint_music/contract.py',
'''    ConstraintRule("CM006", "bass_chord_member", "Every bass pitch belongs to the active triad."),\n''',
'''    ConstraintRule(\n        "CM006", "bass_chord_member", "Every bass pitch belongs to the active local-key triad."\n    ),\n''')
replace('src/constraint_music/contract.py',
'''    ConstraintRule(\n        "CM042",\n        "borrowed_chord_realization",\n        (\n            "Every borrowed beat contains the complete triad derived from its explicit parallel "\n            "source mode and degree, and its serialized inversion agrees with the realized bass."\n        ),\n        conditional=True,\n    ),\n)\n''',
'''    ConstraintRule(\n        "CM042",\n        "borrowed_chord_realization",\n        (\n            "Every borrowed beat contains the complete triad derived from its explicit parallel "\n            "source mode, active key, and degree, and its serialized inversion agrees with bass."\n        ),\n        conditional=True,\n    ),\n    ConstraintRule(\n        "CM043",\n        "key_context_shape",\n        "Enabled modulation serializes exactly one explicit local-key identity per beat.",\n        conditional=True,\n    ),\n    ConstraintRule(\n        "CM044",\n        "modulation_boundary_destination",\n        "The single modulation boundary targets the declared same-mode dominant key.",\n        conditional=True,\n    ),\n    ConstraintRule(\n        "CM045",\n        "modulation_pivot",\n        "The pre-boundary source-tonic triad is an unaltered common chord reinterpretable as destination IV.",\n        conditional=True,\n    ),\n    ConstraintRule(\n        "CM046",\n        "post_modulation_interpretation",\n        "All post-boundary harmony is reconstructed against the persistent destination-key context.",\n        conditional=True,\n    ),\n    ConstraintRule(\n        "CM047",\n        "destination_confirmation",\n        "The destination region closes with an unborrowed, untargeted destination V-I and tonic outer voices.",\n        conditional=True,\n    ),\n    ConstraintRule(\n        "CM048",\n        "serialized_key_context_consistency",\n        "Serialized key contexts equal the exact source-before/destination-after boundary sequence.",\n        conditional=True,\n    ),\n)\n''')

# Provenance schema commits the new semantic axis.
replace('src/constraint_music/provenance.py', 'ARTIFACT_SCHEMA_VERSION = "2.7"', 'ARTIFACT_SCHEMA_VERSION = "2.8"')
replace('src/constraint_music/provenance.py',
'''        "modal_sources",\n    ):\n''',
'''        "modal_sources",\n        "key_contexts",\n    ):\n''')

# Search recognizes key context as a separate axis without redefining harmony.
replace('src/constraint_music/search.py',
'''    "modal_source",\n)\n''',
'''    "modal_source",\n    "key_context",\n)\n''')

replace('src/constraint_music/__init__.py',
'''from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport\n''',
'''from .models import GenerationResult, GenerationSpec, RhythmState, ValidationReport\nfrom .modulation import dominant_key\n''')
replace('src/constraint_music/__init__.py',
'''    "verify_result",\n]\n\n__version__ = "2.7.0a1"\n''',
'''    "verify_result",\n    "dominant_key",\n]\n\n__version__ = "2.8.0a1"\n''')
replace('pyproject.toml', 'version = "2.7.0a1"', 'version = "2.8.0a1"')

print('v2.8 part 1 applied')
