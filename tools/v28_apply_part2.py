from pathlib import Path
from textwrap import dedent

ROOT = Path('.')

def replace(path: str, old: str, new: str) -> None:
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'missing replacement anchor in {path}: {old[:80]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

# SATB becomes active-key-aware while preserving global melody/bass pitch domains.
p = ROOT / 'src/constraint_music/satb.py'
text = p.read_text(encoding='utf-8')
text = text.replace('    Key,\n    is_parallel_perfect,', '    Key,\n    Mode,\n    is_parallel_perfect,', 1)
text = text.replace(
'''    tonicization_targets: tuple[int | None, ...] = ()\n    modal_sources: tuple[ModalSource | None, ...] = ()\n''',
'''    tonicization_targets: tuple[int | None, ...] = ()\n    modal_sources: tuple[ModalSource | None, ...] = ()\n    key_contexts: tuple[Key, ...] = ()\n''', 1)
start = text.index('    @property\n    def chord_form_names')
end = text.index('    def to_dict', start)
new = dedent('''
    @property
    def chord_form_names(self) -> tuple[str, ...]:
        if not (
            len(self.chord_kinds)
            == len(self.chord_inversions)
            == len(self.chord_degrees)
        ):
            return ()
        targets = self.tonicization_targets or (None,) * len(self.chord_degrees)
        sources = self.modal_sources or (None,) * len(self.chord_degrees)
        if not (len(targets) == len(sources) == len(self.chord_degrees)):
            return ()
        names: list[str] = []
        try:
            for beat, (degree, raw_kind, inversion, target, raw_source) in enumerate(
                zip(
                    self.chord_degrees,
                    self.chord_kinds,
                    self.chord_inversions,
                    targets,
                    sources,
                    strict=True,
                )
            ):
                key = self.spec.active_key_at_beat(beat)
                kind = ChordKind.parse(raw_kind)
                source = None if raw_source is None else ModalSource.parse(raw_source)
                if target is not None and source is not None:
                    return ()
                if target is not None:
                    if kind is not ChordKind.SEVENTH:
                        return ()
                    names.append(key.applied_dominant_name(target, inversion))
                elif source is not None:
                    if kind is not ChordKind.TRIAD:
                        return ()
                    names.append(borrowed_chord_name(key, degree, source, inversion))
                else:
                    names.append(key.chord_form_name(degree, kind, inversion))
        except (IndexError, ValueError):
            return ()
        return tuple(names)

''')
text = text[:start] + new + text[end:]
text = text.replace(
'''        if self.modal_sources:\n            music["modal_sources"] = [\n                None if source is None else ModalSource.parse(source).label\n                for source in self.modal_sources\n            ]\n        if self.chord_form_names:\n''',
'''        if self.modal_sources:\n            music["modal_sources"] = [\n                None if source is None else ModalSource.parse(source).label\n                for source in self.modal_sources\n            ]\n        if self.key_contexts:\n            music["key_contexts"] = [\n                {"tonic": key.tonic, "mode": key.mode.value} for key in self.key_contexts\n            ]\n        if self.chord_form_names:\n''', 1)

start = text.index('def result_from_dict(')
end = text.index('\ndef add_satb_constraints(', start)
new = dedent('''
def result_from_dict(payload: Mapping[str, Any]) -> GenerationResult:
    base = GenerationResult.from_dict(payload)
    raw_music = payload.get("music")
    if not isinstance(raw_music, Mapping) or "alto_midi" not in raw_music:
        return base

    def values(key: str) -> tuple[object, ...]:
        value = raw_music.get(key, ())
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ValueError(f"Result JSON music.{key} must be an array")
        return tuple(value)

    def integers(key: str) -> tuple[int, ...]:
        parsed: list[int] = []
        for item in values(key):
            if not isinstance(item, (int, str)):
                raise ValueError(f"Result JSON music.{key} must contain integers")
            try:
                parsed.append(int(item))
            except ValueError as exc:
                raise ValueError(f"Result JSON music.{key} must contain integers") from exc
        return tuple(parsed)

    def optional_integers(key: str) -> tuple[int | None, ...]:
        parsed: list[int | None] = []
        for item in values(key):
            if item is None:
                parsed.append(None)
                continue
            if not isinstance(item, (int, str)):
                raise ValueError(f"Result JSON music.{key} must contain integers or null")
            try:
                parsed.append(int(item))
            except ValueError as exc:
                raise ValueError(f"Result JSON music.{key} must contain integers or null") from exc
        return tuple(parsed)

    def optional_sources(key: str) -> tuple[ModalSource | None, ...]:
        return tuple(None if item is None else ModalSource.parse(item) for item in values(key))

    def contexts(key: str) -> tuple[Key, ...]:
        parsed: list[Key] = []
        for item in values(key):
            if not isinstance(item, Mapping):
                raise ValueError(f"Result JSON music.{key} must contain key objects")
            tonic = item.get("tonic")
            mode = item.get("mode")
            if not isinstance(tonic, str) or not isinstance(mode, str):
                raise ValueError(f"Result JSON music.{key} entries require tonic/mode strings")
            parsed.append(Key(tonic, Mode(mode)))
        return tuple(parsed)

    raw_kinds = values("chord_kinds") if "chord_kinds" in raw_music else ()
    raw_inversions = integers("chord_inversions") if "chord_inversions" in raw_music else ()
    raw_targets = optional_integers("tonicization_targets") if "tonicization_targets" in raw_music else ()
    raw_sources = optional_sources("modal_sources") if "modal_sources" in raw_music else ()
    raw_contexts = contexts("key_contexts") if "key_contexts" in raw_music else ()
    return SatbGenerationResult(
        spec=base.spec,
        melody=base.melody,
        bass=base.bass,
        chord_degrees=base.chord_degrees,
        target_tension=base.target_tension,
        actual_tension=base.actual_tension,
        objective_value=base.objective_value,
        solver_status=base.solver_status,
        wall_time_seconds=base.wall_time_seconds,
        rhythm=base.rhythm,
        validation=base.validation,
        soprano=integers("soprano_midi"),
        alto=integers("alto_midi"),
        tenor=integers("tenor_midi"),
        chord_kinds=tuple(ChordKind.parse(item) for item in raw_kinds),
        chord_inversions=raw_inversions,
        tonicization_targets=raw_targets,
        modal_sources=raw_sources,
        key_contexts=raw_contexts,
    )

''')
text = text[:start] + new + text[end+1:]

start = text.index('def add_satb_constraints(')
end = text.index('\ndef _add_expanded_harmony_motion_constraints(', start)
new = dedent('''
def add_satb_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    melody_note: list[cp_model.IntVar],
    bass_note: list[cp_model.IntVar],
) -> SatbVariables:
    global_key = spec.tonal_key
    soprano_domain = global_key.pitches_in_range(spec.melody_low, spec.melody_high)
    bass_domain = global_key.pitches_in_range(spec.bass_low, spec.bass_high)
    inner_pitch_classes: set[int] = set()
    for key in spec.context_keys:
        inner_pitch_classes.update(key.pitch_classes)
        if spec.tonicization_enabled:
            for target_degree in key.applied_dominant_targets:
                inner_pitch_classes.update(key.applied_dominant_seventh_pitch_classes(target_degree))
        if spec.modal_mixture_enabled:
            source = canonical_modal_source(key)
            for degree in supported_borrowed_degrees(key):
                inner_pitch_classes.update(borrowed_triad_pitch_classes(key, degree, source))
    alto_domain = _pitches_for_pitch_classes(ALTO_LOW, ALTO_HIGH, inner_pitch_classes)
    tenor_domain = _pitches_for_pitch_classes(TENOR_LOW, TENOR_HIGH, inner_pitch_classes)
    if not alto_domain or not tenor_domain:
        raise ValueError("SATB inner-voice ranges contain no pitches in the selected harmony")

    soprano = [model.new_int_var(spec.melody_low, spec.melody_high, f"soprano_{beat}") for beat in range(spec.total_beats)]
    alto = [model.new_int_var(ALTO_LOW, ALTO_HIGH, f"alto_{beat}") for beat in range(spec.total_beats)]
    tenor = [model.new_int_var(TENOR_LOW, TENOR_HIGH, f"tenor_{beat}") for beat in range(spec.total_beats)]
    chord_kind = [model.new_bool_var(f"chord_kind_{beat}") for beat in range(spec.total_beats)]
    chord_inversion = [model.new_int_var(0, 2, f"chord_inversion_{beat}") for beat in range(spec.total_beats)]
    tonicization_target = [
        model.new_int_var(0, NO_TONICIZATION_TARGET, f"tonicization_target_{beat}")
        for beat in range(spec.total_beats)
    ]
    modal_source = [
        model.new_int_var(NO_MODAL_SOURCE, int(ModalSource.PARALLEL_NATURAL_MINOR), f"modal_source_{beat}")
        for beat in range(spec.total_beats)
    ]

    if spec.expanded_harmony_enabled:
        if spec.minimum_seventh_chords:
            model.add(sum(chord_kind) >= spec.minimum_seventh_chords)
        model.add(chord_kind[-1] == int(ChordKind.TRIAD))
    else:
        for kind in chord_kind:
            model.add(kind == int(ChordKind.TRIAD))

    applied_flags: list[cp_model.IntVar] = []
    if spec.tonicization_enabled:
        for beat, target in enumerate(tonicization_target):
            applied = model.new_bool_var(f"applied_dominant_{beat}")
            model.add(target != NO_TONICIZATION_TARGET).only_enforce_if(applied)
            model.add(target == NO_TONICIZATION_TARGET).only_enforce_if(applied.negated())
            applied_flags.append(applied)
        if spec.minimum_applied_dominants:
            model.add(sum(applied_flags) >= spec.minimum_applied_dominants)
        model.add(tonicization_target[-1] == NO_TONICIZATION_TARGET)
    else:
        for target in tonicization_target:
            model.add(target == NO_TONICIZATION_TARGET)

    borrowed_flags: list[cp_model.IntVar] = []
    if spec.modal_mixture_enabled:
        for beat, source_var in enumerate(modal_source):
            canonical_source = int(canonical_modal_source(spec.active_key_at_beat(beat)))
            model.add_allowed_assignments([source_var], [(NO_MODAL_SOURCE,), (canonical_source,)])
            borrowed = model.new_bool_var(f"borrowed_chord_{beat}")
            model.add(source_var == canonical_source).only_enforce_if(borrowed)
            model.add(source_var == NO_MODAL_SOURCE).only_enforce_if(borrowed.negated())
            borrowed_flags.append(borrowed)
        if spec.minimum_borrowed_chords:
            model.add(sum(borrowed_flags) >= spec.minimum_borrowed_chords)
        model.add(modal_source[-1] == NO_MODAL_SOURCE)
        if spec.require_authentic_cadence and spec.total_beats >= 2:
            model.add(modal_source[-2] == NO_MODAL_SOURCE)
    else:
        for source_var in modal_source:
            model.add(source_var == NO_MODAL_SOURCE)

    if spec.modulation_enabled:
        boundary = spec.modulation_boundary_beat
        if boundary is None:
            raise ValueError("Validated modulation spec lost boundary")
        reserved = {0, boundary - 1, spec.total_beats - 2, spec.total_beats - 1}
        for beat in reserved:
            model.add(tonicization_target[beat] == NO_TONICIZATION_TARGET)
            model.add(modal_source[beat] == NO_MODAL_SOURCE)
        model.add(chord_kind[0] == int(ChordKind.TRIAD))
        model.add(chord_kind[boundary - 1] == int(ChordKind.TRIAD))

    pitch_classes: list[list[cp_model.IntVar]] = []
    for beat in range(spec.total_beats):
        strong_step = beat * spec.subdivisions_per_beat
        model.add(soprano[beat] == melody_note[strong_step])
        model.add_allowed_assignments([alto[beat]], [(note,) for note in alto_domain])
        model.add_allowed_assignments([tenor[beat]], [(note,) for note in tenor_domain])
        model.add(bass_note[beat] < tenor[beat])
        model.add(tenor[beat] < alto[beat])
        model.add(alto[beat] < soprano[beat])
        model.add(soprano[beat] - alto[beat] <= MAX_UPPER_SPACING)
        model.add(alto[beat] - tenor[beat] <= MAX_UPPER_SPACING)
        pcs = [model.new_int_var(0, 11, f"satb_pc_{beat}_{index}") for index in range(4)]
        pitch_classes.append(pcs)
        for pc, note_var in zip(pcs, (soprano[beat], alto[beat], tenor[beat], bass_note[beat]), strict=True):
            model.add_modulo_equality(pc, note_var, 12)
        rows = _satb_chord_rows(
            spec.active_key_at_beat(beat),
            spec.expanded_harmony_enabled,
            spec.tonicization_enabled,
            spec.modal_mixture_enabled,
        )
        model.add_allowed_assignments(
            [chord[beat], chord_kind[beat], chord_inversion[beat], tonicization_target[beat], modal_source[beat], *pcs],
            rows,
        )

    if spec.avoid_parallel_perfects:
        pair_domains = (
            (soprano, alto, soprano_domain, alto_domain),
            (soprano, tenor, soprano_domain, tenor_domain),
            (alto, tenor, alto_domain, tenor_domain),
            (alto, bass_note, alto_domain, bass_domain),
            (tenor, bass_note, tenor_domain, bass_domain),
        )
        for left_voice, right_voice, left_domain, right_domain in pair_domains:
            forbidden = _parallel_rows(left_domain, right_domain)
            for beat in range(spec.total_beats - 1):
                model.add_forbidden_assignments(
                    [left_voice[beat], right_voice[beat], left_voice[beat + 1], right_voice[beat + 1]],
                    forbidden,
                )

    if spec.resolve_leading_tone:
        for voice_vars, domain in ((alto, alto_domain), (tenor, tenor_domain)):
            for beat, (left_var, right_var) in enumerate(pairwise(voice_vars)):
                key = spec.active_key_at_beat(beat)
                allowed = [
                    (left_note, right_note)
                    for left_note in domain
                    for right_note in domain
                    if left_note % 12 != key.leading_tone_pc or right_note == left_note + 1
                ]
                model.add_allowed_assignments([left_var, right_var], allowed)

    if spec.expanded_harmony_enabled:
        _add_expanded_harmony_motion_constraints(
            model, spec, chord, chord_kind, tonicization_target, pitch_classes,
            soprano, alto, tenor, bass_note,
        )

    return SatbVariables(
        soprano=soprano,
        alto=alto,
        tenor=tenor,
        chord_kind=chord_kind,
        chord_inversion=chord_inversion,
        tonicization_target=tonicization_target,
        modal_source=modal_source,
    )

''')
text = text[:start] + new + text[end+1:]

start = text.index('def _add_expanded_harmony_motion_constraints(')
end = text.index('\ndef satb_verification_issues(', start)
new = dedent('''
def _add_expanded_harmony_motion_constraints(
    model: cp_model.CpModel,
    spec: GenerationSpec,
    chord: list[cp_model.IntVar],
    chord_kind: list[cp_model.IntVar],
    tonicization_target: list[cp_model.IntVar],
    pitch_classes: list[list[cp_model.IntVar]],
    soprano: list[cp_model.IntVar],
    alto: list[cp_model.IntVar],
    tenor: list[cp_model.IntVar],
    bass: list[cp_model.IntVar],
) -> None:
    global_dominant_rows = _global_dominant_seventh_flag_rows()
    voices = (soprano, alto, tenor, bass)
    for beat in range(len(chord) - 1):
        key = spec.active_key_at_beat(beat)
        seventh_rows = _chordal_seventh_flag_rows(key, spec.tonicization_enabled)
        leading_rows = _dominant_leading_flag_rows(key, spec.tonicization_enabled)
        target = tonicization_target[beat]
        applied = model.new_bool_var(f"motion_applied_dominant_{beat}")
        model.add(target != NO_TONICIZATION_TARGET).only_enforce_if(applied)
        model.add(target == NO_TONICIZATION_TARGET).only_enforce_if(applied.negated())
        model.add(chord[beat + 1] == target).only_enforce_if(applied)
        model.add(tonicization_target[beat + 1] == NO_TONICIZATION_TARGET).only_enforce_if(applied)
        global_dominant = model.new_bool_var(f"global_dominant_seventh_{beat}")
        model.add_allowed_assignments(
            [chord[beat], chord_kind[beat], target, global_dominant], global_dominant_rows
        )
        model.add(chord[beat + 1] == 0).only_enforce_if(global_dominant)
        for voice_index, voice in enumerate(voices):
            current_pc = pitch_classes[beat][voice_index]
            carries_seventh = model.new_bool_var(f"chordal_seventh_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [chord[beat], chord_kind[beat], target, current_pc, carries_seventh], seventh_rows
            )
            model.add(voice[beat + 1] <= voice[beat] - 1).only_enforce_if(carries_seventh)
            model.add(voice[beat + 1] >= voice[beat] - 2).only_enforce_if(carries_seventh)
            carries_leading = model.new_bool_var(f"dominant_leading_{beat}_{voice_index}")
            model.add_allowed_assignments(
                [chord[beat], chord_kind[beat], target, current_pc, carries_leading], leading_rows
            )
            model.add(voice[beat + 1] == voice[beat] + 1).only_enforce_if(carries_leading)

''')
text = text[:start] + new + text[end+1:]

start = text.index('def satb_verification_issues(')
end = text.index('\ndef _verify_expanded_harmony_motion(', start)
new = dedent('''
def satb_verification_issues(result: GenerationResult) -> tuple[tuple[str, str], ...]:
    if not isinstance(result, SatbGenerationResult):
        return ()
    spec = result.spec
    soprano, alto, tenor, bass = result.soprano, result.alto, result.tenor, result.bass
    issues: list[tuple[str, str]] = []
    if not all(len(voice) == spec.total_beats for voice in (soprano, alto, tenor, bass)):
        issues.append(("CM027", "SATB voices must contain exactly one note per beat"))
        return tuple(issues)
    for beat, note in enumerate(soprano):
        strong_step = beat * spec.subdivisions_per_beat
        if strong_step >= len(result.melody) or note != result.melody[strong_step]:
            issues.append(("CM027", f"Beat {beat}: soprano is not anchored to strong-step melody"))

    metadata_present = bool(result.chord_kinds or result.chord_inversions)
    metadata_valid = False
    kinds: tuple[ChordKind, ...] = (ChordKind.TRIAD,) * spec.total_beats
    inversions: tuple[int, ...] = ()
    if metadata_present:
        if not (len(result.chord_kinds) == len(result.chord_inversions) == spec.total_beats):
            issues.append(("CM033", "Harmonic kind/inversion arrays must contain one value per beat"))
        else:
            try:
                kinds = tuple(ChordKind.parse(item) for item in result.chord_kinds)
            except ValueError:
                issues.append(("CM033", "Harmonic form contains an unknown chord kind"))
            else:
                inversions = tuple(int(item) for item in result.chord_inversions)
                metadata_valid = True
                if any(not 0 <= inversion <= 2 for inversion in inversions):
                    issues.append(("CM033", "Chord inversions must be encoded in 0..2"))
                if not spec.expanded_harmony_enabled and any(k is ChordKind.SEVENTH for k in kinds):
                    issues.append(("CM033", "Seventh chords require harmony_vocabulary='triads+sevenths'"))
                if sum(k is ChordKind.SEVENTH for k in kinds) < spec.minimum_seventh_chords:
                    issues.append(("CM033", "Serialized harmony does not meet minimum_seventh_chords"))
    elif spec.expanded_harmony_enabled:
        issues.append(("CM033", "Expanded harmony requires explicit chord kind/inversion metadata"))

    targets_present = bool(result.tonicization_targets)
    targets: tuple[int | None, ...] = (None,) * spec.total_beats
    context_valid = False
    if targets_present:
        if len(result.tonicization_targets) != spec.total_beats:
            issues.append(("CM037", "Tonicization target metadata must contain one value per beat"))
        else:
            targets = result.tonicization_targets
            context_valid = True
    elif spec.tonicization_enabled:
        issues.append(("CM037", "Enabled tonicization requires explicit target metadata"))
    else:
        context_valid = True
    applied_count = 0
    if context_valid:
        for beat, target in enumerate(targets):
            if target is None:
                continue
            applied_count += 1
            key = spec.active_key_at_beat(beat)
            if not spec.tonicization_enabled:
                issues.append(("CM037", f"Beat {beat}: tonicization is not enabled by the spec"))
                continue
            if target not in key.applied_dominant_targets:
                issues.append(("CM037", f"Beat {beat}: unsupported tonicization target {target} in {key}"))
                continue
            if metadata_valid and kinds[beat] is not ChordKind.SEVENTH:
                issues.append(("CM037", f"Beat {beat}: applied dominant must be a seventh chord"))
        if applied_count < spec.minimum_applied_dominants:
            issues.append(("CM037", "Serialized harmony does not meet minimum_applied_dominants"))

    source_metadata_present = bool(result.modal_sources)
    sources: tuple[ModalSource | None, ...] = (None,) * spec.total_beats
    source_context_valid = False
    if source_metadata_present:
        if len(result.modal_sources) != spec.total_beats:
            issues.append(("CM041", "Modal source metadata must contain one value per beat"))
        else:
            try:
                sources = tuple(None if s is None else ModalSource.parse(s) for s in result.modal_sources)
            except ValueError:
                issues.append(("CM041", "Modal source metadata contains an unknown source"))
            else:
                source_context_valid = True
    elif spec.modal_mixture_enabled:
        issues.append(("CM041", "Enabled modal mixture requires explicit source metadata"))
    else:
        source_context_valid = True
    borrowed_count = 0
    if source_context_valid:
        for beat, source in enumerate(sources):
            if source is None:
                continue
            borrowed_count += 1
            key = spec.active_key_at_beat(beat)
            canonical_source = canonical_modal_source(key)
            supported_borrowed = set(supported_borrowed_degrees(key))
            if not spec.modal_mixture_enabled:
                issues.append(("CM041", f"Beat {beat}: modal mixture is not enabled by the spec"))
                continue
            if source is not canonical_source:
                issues.append(("CM041", f"Beat {beat}: modal source {source.label} is not canonical for {key}"))
                continue
            if beat == spec.total_beats - 1:
                issues.append(("CM041", f"Beat {beat}: final chord must remain unborrowed"))
            if (spec.require_authentic_cadence or spec.modulation_enabled) and beat == spec.total_beats - 2:
                issues.append(("CM041", f"Beat {beat}: cadential dominant must remain unborrowed"))
            if beat < len(result.chord_degrees) and result.chord_degrees[beat] not in supported_borrowed:
                issues.append(("CM041", f"Beat {beat}: degree {result.chord_degrees[beat]} is not borrowable in {key}"))
            if context_valid and targets[beat] is not None:
                issues.append(("CM041", f"Beat {beat}: borrowing and tonicization cannot coexist"))
            if metadata_valid and kinds[beat] is not ChordKind.TRIAD:
                issues.append(("CM041", f"Beat {beat}: borrowed harmony must be triadic"))
        if borrowed_count < spec.minimum_borrowed_chords:
            issues.append(("CM041", "Serialized harmony does not meet minimum_borrowed_chords"))

    for beat, (sv, av, tv, bv) in enumerate(zip(soprano, alto, tenor, bass, strict=True)):
        if not spec.melody_low <= sv <= spec.melody_high:
            issues.append(("CM028", f"Beat {beat}: soprano is outside its configured range"))
        if not ALTO_LOW <= av <= ALTO_HIGH:
            issues.append(("CM028", f"Beat {beat}: alto is outside {ALTO_LOW}..{ALTO_HIGH}"))
        if not TENOR_LOW <= tv <= TENOR_HIGH:
            issues.append(("CM028", f"Beat {beat}: tenor is outside {TENOR_LOW}..{TENOR_HIGH}"))
        if not bv < tv < av < sv:
            issues.append(("CM028", f"Beat {beat}: SATB voice order/crossing invariant is violated"))
        if sv - av > MAX_UPPER_SPACING or av - tv > MAX_UPPER_SPACING:
            issues.append(("CM029", f"Beat {beat}: adjacent upper voices exceed octave spacing"))
        if beat >= len(result.chord_degrees) or not 0 <= result.chord_degrees[beat] <= 6:
            continue
        key = spec.active_key_at_beat(beat)
        degree = result.chord_degrees[beat]
        pcs = (sv % 12, av % 12, tv % 12, bv % 12)
        kind = kinds[beat] if metadata_valid else ChordKind.TRIAD
        target = targets[beat] if context_valid else None
        source = sources[beat] if source_context_valid else None
        if target is not None:
            if target not in key.applied_dominant_targets or not metadata_valid:
                continue
            expected_degree = key.applied_dominant_root_degree(target)
            applied_pcs = key.applied_dominant_seventh_pitch_classes(target)
            if degree != expected_degree:
                issues.append(("CM038", f"Beat {beat}: applied-dominant root degree does not match target {target}"))
            if kind is not ChordKind.SEVENTH or set(pcs) != set(applied_pcs) or len(set(pcs)) != 4:
                issues.append(("CM038", f"Beat {beat}: applied dominant is not a complete dominant seventh"))
            if 0 <= inversions[beat] <= 2 and bv % 12 != applied_pcs[inversions[beat]]:
                issues.append(("CM038", f"Beat {beat}: applied-dominant inversion does not match bass"))
            continue
        if source is not None:
            canonical_source = canonical_modal_source(key)
            supported_borrowed = set(supported_borrowed_degrees(key))
            if not metadata_valid or source is not canonical_source or degree not in supported_borrowed:
                continue
            borrowed_pcs = borrowed_triad_pitch_classes(key, degree, source)
            if kind is not ChordKind.TRIAD or set(pcs) != set(borrowed_pcs) or len(set(pcs)) != 3:
                issues.append(("CM042", f"Beat {beat}: borrowed chord is not complete active-key source triad"))
            if 0 <= inversions[beat] <= 2 and bv % 12 != borrowed_pcs[inversions[beat]]:
                issues.append(("CM042", f"Beat {beat}: borrowed-chord inversion does not match bass"))
            continue
        if kind is ChordKind.TRIAD:
            triad = key.triad_pitch_classes(degree)
            root = triad[0]
            if any(pc not in triad for pc in pcs) or set(pcs) != set(triad) or pcs.count(root) < 2:
                issues.append(("CM030", f"Beat {beat}: active-key SATB triad is incomplete or root is not doubled"))
        elif metadata_valid:
            seventh = key.seventh_pitch_classes(degree)
            if set(pcs) != set(seventh) or len(set(pcs)) != 4:
                issues.append(("CM034", f"Beat {beat}: active-key seventh chord is incomplete"))
        if metadata_valid:
            chord_tones = key.triad_pitch_classes(degree) if kind is ChordKind.TRIAD else key.seventh_pitch_classes(degree)
            inversion = inversions[beat]
            if 0 <= inversion <= 2 and bv % 12 != chord_tones[inversion]:
                issues.append(("CM034", f"Beat {beat}: serialized inversion does not match bass"))

    if spec.avoid_parallel_perfects:
        for label, left_voice, right_voice in (
            ("S-A", soprano, alto), ("S-T", soprano, tenor), ("A-T", alto, tenor),
            ("A-B", alto, bass), ("T-B", tenor, bass),
        ):
            for beat in range(min(len(left_voice), len(right_voice)) - 1):
                if is_parallel_perfect(left_voice[beat], right_voice[beat], left_voice[beat + 1], right_voice[beat + 1]):
                    issues.append(("CM031", f"Beats {beat}->{beat + 1}: parallel perfect in {label}"))
    if spec.resolve_leading_tone:
        for label, voice in (("alto", alto), ("tenor", tenor)):
            for beat, (left, right) in enumerate(pairwise(voice)):
                key = spec.active_key_at_beat(beat)
                if left % 12 == key.leading_tone_pc and right != left + 1:
                    issues.append(("CM032", f"{label} beat {beat}: active-key leading tone does not resolve upward"))
    if metadata_valid and context_valid:
        _verify_expanded_harmony_motion(result, kinds, targets, issues)
    return tuple(issues)

''')
text = text[:start] + new + text[end+1:]

start = text.index('def _verify_expanded_harmony_motion(')
end = text.index('\n\n@cache\ndef _satb_chord_rows(', start)
new = dedent('''
def _verify_expanded_harmony_motion(
    result: SatbGenerationResult,
    kinds: tuple[ChordKind, ...],
    targets: tuple[int | None, ...],
    issues: list[tuple[str, str]],
) -> None:
    voices = (
        ("soprano", result.soprano), ("alto", result.alto),
        ("tenor", result.tenor), ("bass", result.bass),
    )
    beats = min(len(result.chord_degrees), len(kinds), len(targets))
    for beat in range(beats):
        if kinds[beat] is not ChordKind.SEVENTH:
            continue
        key = result.spec.active_key_at_beat(beat)
        target = targets[beat]
        if target is not None:
            if target not in key.applied_dominant_targets:
                continue
            if beat + 1 >= beats:
                issues.append(("CM039", f"Beat {beat}: applied dominant has no target resolution"))
                continue
            if result.chord_degrees[beat + 1] != target or targets[beat + 1] is not None:
                issues.append(("CM039", f"Beat {beat}: applied dominant does not resolve to declared target"))
            applied_pcs = key.applied_dominant_seventh_pitch_classes(target)
            seventh_pc, leading_pc = applied_pcs[3], applied_pcs[1]
            for label, voice in voices:
                if voice[beat] % 12 == seventh_pc and voice[beat + 1] - voice[beat] not in {-1, -2}:
                    issues.append(("CM040", f"{label} beat {beat}: applied chordal seventh does not resolve down"))
                if voice[beat] % 12 == leading_pc and voice[beat + 1] != voice[beat] + 1:
                    issues.append(("CM040", f"{label} beat {beat}: applied leading tone does not resolve upward"))
            continue
        if beat + 1 >= beats:
            issues.append(("CM035", f"Beat {beat}: chordal seventh has no following resolution"))
            continue
        degree = result.chord_degrees[beat]
        if not 0 <= degree <= 6:
            continue
        seventh_pc = key.seventh_pitch_classes(degree)[3]
        for label, voice in voices:
            if voice[beat] % 12 == seventh_pc and voice[beat + 1] - voice[beat] not in {-1, -2}:
                issues.append(("CM035", f"{label} beat {beat}: chordal seventh does not resolve down by step"))
        if degree == 4:
            if result.chord_degrees[beat + 1] != 0:
                issues.append(("CM036", f"Beat {beat}: active-key dominant seventh does not resolve to tonic"))
            for label, voice in voices:
                if voice[beat] % 12 == key.leading_tone_pc and voice[beat + 1] != voice[beat] + 1:
                    issues.append(("CM036", f"{label} beat {beat}: active-key dominant leading tone does not resolve upward"))
''')
text = text[:start] + new + text[end:]
p.write_text(text, encoding='utf-8')

# Solver emits deterministic key contexts and exposes them as a distinct semantic axis.
replace('src/constraint_music/solver.py',
'''                "mixture, repetition, or distinctness constraints."\n''',
'''                "mixture, modulation, repetition, or distinctness constraints."\n''')
replace('src/constraint_music/solver.py',
'''            modal_sources=tuple(\n                None if value == NO_MODAL_SOURCE else ModalSource(value)\n                for value in (solver.value(item) for item in problem.satb.modal_source)\n            ),\n        )\n''',
'''            modal_sources=tuple(\n                None if value == NO_MODAL_SOURCE else ModalSource(value)\n                for value in (solver.value(item) for item in problem.satb.modal_source)\n            ),\n            key_contexts=spec.expected_key_contexts if spec.modulation_enabled else (),\n        )\n''')
replace('src/constraint_music/solver.py',
'''        if "modal_source" in distinct_on:\n            if not isinstance(result, SatbGenerationResult):\n                raise ValueError("modal_source distinctness requires a SATB result")\n            if len(result.modal_sources) != len(problem.chord):\n                raise ValueError("modal_source distinctness requires explicit source metadata")\n            variables.extend(\n                (\n                    variable,\n                    NO_MODAL_SOURCE if source is None else int(ModalSource.parse(source)),\n                )\n                for variable, source in zip(\n                    problem.satb.modal_source,\n                    result.modal_sources,\n                    strict=True,\n                )\n            )\n\n        differs: list[cp_model.IntVar] = []\n''',
'''        if "modal_source" in distinct_on:\n            if not isinstance(result, SatbGenerationResult):\n                raise ValueError("modal_source distinctness requires a SATB result")\n            if len(result.modal_sources) != len(problem.chord):\n                raise ValueError("modal_source distinctness requires explicit source metadata")\n            variables.extend(\n                (\n                    variable,\n                    NO_MODAL_SOURCE if source is None else int(ModalSource.parse(source)),\n                )\n                for variable, source in zip(\n                    problem.satb.modal_source,\n                    result.modal_sources,\n                    strict=True,\n                )\n            )\n        if "key_context" in distinct_on:\n            if not isinstance(result, SatbGenerationResult):\n                raise ValueError("key_context distinctness requires a SATB result")\n            if result.spec.modulation_enabled and len(result.key_contexts) != len(problem.chord):\n                raise ValueError("key_context distinctness requires explicit context metadata")\n            # v2.8 key context is spec-bound. With this as the only dimension, the second\n            # no-good intentionally becomes contradictory: there is exactly one context sequence.\n\n        differs: list[cp_model.IntVar] = []\n''')

# Documentation and example.
(ROOT / 'docs/MODULATION.md').write_text(dedent('''
# Explicit Modulation and Local Key Context (v2.8)

v2.8 distinguishes **tonicization** from **modulation**. Tonicization remains a one-chord local-target event. Modulation changes the persistent active key used to interpret chord degrees after an explicit boundary.

The first certified scope is deliberately narrow: one same-mode move from the global key to its dominant key, using the source-tonic triad as a common-chord pivot (`I` in the source, `IV` in the destination), followed by a persistent destination region and an unborrowed/untargeted destination `V-I` close.

```yaml
require_authentic_cadence: false
modulation_enabled: true
modulation_destination_key: G
modulation_boundary_beat: 4
```

For C major with boundary 4, beats 0–3 carry `C major`; beat 3 is the certified common pivot; beats 4 onward carry `G major`. The global key stored in the specification never changes.

## Compatibility boundary

`CM002` and `CM003` retain the original global-key pitch-domain restriction for melody and bass. v2.8 explicitly revisions `CM005`/`CM006` so chord membership follows the active local key when modulation is enabled. Inner voices may therefore carry destination-key chromatic tones while the outer voices remain inside the established global pitch domain.

The legacy `CM016` whole-piece authentic cadence remains global-key semantics and is mutually exclusive with v2.8 modulation. Destination confirmation is instead certified by `CM047`.

## Interactions

Applied-dominant tonicization and modal mixture continue to use explicit metadata, but after the boundary they are derived from the **destination key**, not the original key. The pivot, opening source tonic, and final destination cadence are protected from tonicization/borrowing. Explicit phrase grammar is deferred for modulation in v2.8 rather than being partially reinterpreted.

## New contract rules

- `CM043` key-context shape
- `CM044` modulation boundary/destination policy
- `CM045` exact common-pivot realization
- `CM046` post-modulation active-key interpretation
- `CM047` destination-key confirmation
- `CM048` serialized key-context consistency

Artifact schema 2.8 commits `key_contexts` into the semantic composition digest. Old artifacts remain loadable when modulation is disabled and do not receive invented context metadata.
''').lstrip(), encoding='utf-8')
(ROOT / 'examples/modulation.yaml').write_text(dedent('''
key: C
mode: major
bars: 2
beats_per_bar: 4
subdivisions_per_beat: 1
require_authentic_cadence: false
modulation_enabled: true
modulation_destination_key: G
modulation_boundary_beat: 4
workers: 1
seed: 2808
max_time_seconds: 30
''').lstrip(), encoding='utf-8')

replace('README.md',
'> Current release line: **2.7.0a1** — verified modal mixture with explicit parallel-source identity, source-derived borrowed triads, and independently checked realization.',
'> Current release line: **2.8.0a1** — explicit persistent local-key context with independently verified dominant-key modulation.')
replace('README.md', 'independent 42-rule verifier + objective-vector recomputation', 'independent 48-rule verifier + objective-vector recomputation')
insert_anchor = '## Hard-constraint contract\n'
section = dedent('''
## v2.8: explicit modulation and persistent local key

Modulation is now a separate opt-in semantic axis rather than a relabeled tonicization event. The bounded first implementation supports one same-mode move to the dominant key through an exact common-chord pivot, after which chord degrees, sevenths, applied dominants, and modal borrowing are interpreted in the persistent destination context.

```yaml
require_authentic_cadence: false
modulation_enabled: true
modulation_destination_key: G
modulation_boundary_beat: 4
```

The global key never mutates. Artifacts serialize one `key_context` per beat and schema 2.8 commits that sequence to provenance. The legacy global pitch-domain constraints remain intact; the versioned v2.8 revision makes CM005/CM006 chord membership follow the active local key after the boundary.

See [Explicit Modulation and Local Key Context](docs/MODULATION.md).

''')
replace('README.md', insert_anchor, section + insert_anchor)
replace('README.md', 'v2.7 extends the certification contract to **42 stable hard-rule IDs**.', 'v2.8 extends the certification contract to **48 stable hard-rule IDs**.')
replace('README.md', '`CM041`–`CM042` certify modal-source context and exact source-derived borrowed-triad realization.', '`CM041`–`CM042` certify modal-source context and exact source-derived borrowed-triad realization; `CM043`–`CM048` certify persistent key context, pivot identity, post-boundary interpretation, and destination confirmation.')
replace('README.md', 'rechecks all 42 hard rules plus artifact schema', 'rechecks all 48 hard rules plus artifact schema')
replace('README.md', 'Artifact schema `2.7` commits SATB voices, harmonic form, tonicization targets, and modal-source metadata when present.', 'Artifact schema `2.8` additionally commits explicit per-beat key-context metadata when modulation is enabled.')
replace('README.md', '[Modal Mixture](docs/MODAL_MIXTURE.md), and [Verification](docs/VERIFICATION.md).', '[Modal Mixture](docs/MODAL_MIXTURE.md), [Explicit Modulation](docs/MODULATION.md), and [Verification](docs/VERIFICATION.md).')
replace('README.md', 'persistent local-key regions, pivot-chord modulation, and third-inversion sevenths remain outside this release rather than being represented partially.', 'arbitrary modulation chains, distant/enharmonic key networks, phrase-grammar reinterpretation across modulation, and third-inversion sevenths remain outside this release rather than being represented partially.')

replace('docs/ROADMAP.md',
'''- [ ] Persistent local-key regions distinct from one-chord tonicization.\n- [ ] Controlled modulation with explicit pivot and destination-key identity.\n''',
'''- [x] Persistent local-key regions distinct from one-chord tonicization.\n- [x] Controlled modulation with explicit pivot and destination-key identity.\n- [ ] Arbitrary modulation chains, distant keys, and enharmonic reinterpretation.\n''')

# Prepend changelog entry.
p = ROOT / 'CHANGELOG.md'
old = p.read_text(encoding='utf-8')
entry = dedent('''
## 2.8.0a1

- Added one explicit persistent same-mode modulation to the dominant key with a certified common-chord pivot.
- Added per-beat key-context metadata and schema/contract 2.8 provenance coverage.
- Versioned CM005/CM006 active-local-key semantics while preserving the global melody/bass pitch domains.
- Made tonicization, modal mixture, seventh realization, and tendency checks destination-key-aware after modulation.
- Added CM043–CM048 and adversarial modulation/context tests.

''')
p.write_text(entry + old, encoding='utf-8')
for path, note in (
    ('docs/ARCHITECTURE.md', '\n\n## v2.8 local-key state\n\nThe global key is immutable. When modulation is enabled, `GenerationSpec.active_key_at_beat()` derives a persistent source-before/destination-after key context from the explicit boundary. Solver tables and independent SATB verification consume that active key separately from the original global pitch domains.\n'),
    ('docs/VERIFICATION.md', '\n\n## v2.8 modulation verification\n\nCM043–CM048 independently reconstruct the dominant-key destination, exact common pivot, per-beat context sequence, post-boundary harmonic interpretation, and destination V-I confirmation. `key_contexts` is also included in the semantic provenance digest.\n'),
    ('docs/HISTORY.md', '\n- **v2.8** — explicit persistent local-key context and verified dominant-key modulation (CM043–CM048).\n'),
):
    q = ROOT / path
    q.write_text(q.read_text(encoding='utf-8').rstrip() + note, encoding='utf-8')

# Adversarial/interaction tests.
(ROOT / 'tests/test_modulation.py').write_text(dedent('''
from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from constraint_music.contract import HARD_CONSTRAINT_IDS
from constraint_music.models import GenerationSpec
from constraint_music.modulation import dominant_key
from constraint_music.provenance import artifact_payload, verify_artifact_integrity
from constraint_music.satb import SatbGenerationResult, result_from_dict
from constraint_music.search import DISTINCT_DIMENSIONS
from constraint_music.solver import ConstraintMusicSolver, NoSolutionError
from constraint_music.theory import Key, Mode
from constraint_music.verifier import verify_result


def base_spec(**changes: object) -> GenerationSpec:
    values: dict[str, object] = {
        "bars": 2,
        "beats_per_bar": 4,
        "subdivisions_per_beat": 1,
        "require_authentic_cadence": False,
        "modulation_enabled": True,
        "modulation_destination_key": "G",
        "modulation_boundary_beat": 2,
        "avoid_parallel_perfects": False,
        "workers": 1,
        "seed": 2808,
        "max_time_seconds": 30,
        "tension_curve": (0.05, 0.15, 0.35, 0.55, 0.75, 0.9, 0.6, 0.1),
    }
    values.update(changes)
    return GenerationSpec(**values)


@cache
def modulated_piece() -> SatbGenerationResult:
    result = ConstraintMusicSolver().generate(base_spec())
    assert isinstance(result, SatbGenerationResult)
    return result


def test_dominant_destination_policy_and_configuration_fail_closed() -> None:
    assert dominant_key(Key("C", Mode.MAJOR)) == Key("G", Mode.MAJOR)
    with pytest.raises(ValueError, match="require_authentic_cadence=false"):
        GenerationSpec(modulation_enabled=True, modulation_destination_key="G", modulation_boundary_beat=2)
    with pytest.raises(ValueError, match="same-mode dominant key G"):
        base_spec(modulation_destination_key="F")
    with pytest.raises(ValueError, match="modulation_boundary_beat"):
        base_spec(modulation_boundary_beat=1)


def test_solver_emits_verified_persistent_destination_context() -> None:
    result = modulated_piece()
    assert result.validation.valid, result.validation.issues
    assert result.validation.checked_rules == HARD_CONSTRAINT_IDS
    assert len(HARD_CONSTRAINT_IDS) == 48
    assert result.key_contexts[:2] == (Key("C", Mode.MAJOR),) * 2
    assert result.key_contexts[2:] == (Key("G", Mode.MAJOR),) * 6
    assert result.chord_degrees[1] == 0
    assert result.chord_degrees[-2:] == (4, 0)
    assert result.soprano[-1] % 12 == Key("G", Mode.MAJOR).tonic_pc
    assert result.bass[-1] % 12 == Key("G", Mode.MAJOR).tonic_pc


def test_shifted_or_forged_key_context_is_rejected() -> None:
    result = modulated_piece()
    contexts = list(result.key_contexts)
    contexts[2] = Key("C", Mode.MAJOR)
    report = verify_result(replace(result, key_contexts=tuple(contexts)))
    assert not report.valid
    assert "CM048" in report.failed_rules


def test_forged_pivot_and_destination_cadence_are_rejected() -> None:
    result = modulated_piece()
    chords = list(result.chord_degrees)
    chords[1] = 3
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM045" in report.failed_rules
    chords = list(result.chord_degrees)
    chords[-2] = 3
    report = verify_result(replace(result, chord_degrees=tuple(chords)))
    assert not report.valid
    assert "CM047" in report.failed_rules


def test_key_context_tampering_breaks_semantic_provenance() -> None:
    result = modulated_piece()
    payload = artifact_payload(result)
    payload["music"]["key_contexts"][2] = {"tonic": "C", "mode": "major"}
    tampered = result_from_dict(payload)
    issues = verify_artifact_integrity(tampered, payload)
    assert "composition digest mismatch" in issues
    assert "artifact content digest mismatch" in issues


def test_old_payload_without_key_context_remains_loadable_when_modulation_is_off() -> None:
    legacy = ConstraintMusicSolver().generate(
        GenerationSpec(bars=1, beats_per_bar=4, subdivisions_per_beat=1, workers=1, seed=2707)
    )
    assert isinstance(legacy, SatbGenerationResult)
    payload = legacy.to_dict()
    payload["music"].pop("key_contexts", None)
    loaded = result_from_dict(payload)
    assert isinstance(loaded, SatbGenerationResult)
    assert loaded.key_contexts == ()
    assert verify_result(loaded).valid


def test_key_context_is_separate_search_axis_and_spec_bound() -> None:
    assert "key_context" in DISTINCT_DIMENSIONS
    with pytest.raises(NoSolutionError, match="Only 1 distinct compositions"):
        ConstraintMusicSolver().generate_many(base_spec(seed=2810), 2, ("key_context",))


def test_modulation_followed_by_destination_tonicization() -> None:
    result = ConstraintMusicSolver().generate(
        base_spec(
            harmony_vocabulary="triads+sevenths",
            tonicization_enabled=True,
            minimum_applied_dominants=1,
            seed=2811,
        )
    )
    assert isinstance(result, SatbGenerationResult)
    beats = [i for i, target in enumerate(result.tonicization_targets) if target is not None]
    assert beats and all(beat >= 2 for beat in beats)
    assert verify_result(result).valid


def test_modulation_followed_by_destination_modal_mixture() -> None:
    result = ConstraintMusicSolver().generate(
        base_spec(modal_mixture_enabled=True, minimum_borrowed_chords=1, seed=2812)
    )
    assert isinstance(result, SatbGenerationResult)
    beats = [i for i, source in enumerate(result.modal_sources) if source is not None]
    assert beats and all(beat >= 2 for beat in beats)
    assert verify_result(result).valid


def test_post_modulation_borrowing_is_derived_from_destination_not_stale_source_key() -> None:
    result = ConstraintMusicSolver().generate(
        base_spec(modal_mixture_enabled=True, minimum_borrowed_chords=1, seed=2813)
    )
    assert isinstance(result, SatbGenerationResult)
    beat = next(i for i, source in enumerate(result.modal_sources) if source is not None)
    assert beat >= 2
    # Removing the destination context while leaving borrowed metadata/notes intact must fail.
    contexts = list(result.key_contexts)
    contexts[beat] = Key("C", Mode.MAJOR)
    report = verify_result(replace(result, key_contexts=tuple(contexts)))
    assert not report.valid
    assert "CM048" in report.failed_rules
''').lstrip(), encoding='utf-8')

print('v2.8 part 2 applied')
