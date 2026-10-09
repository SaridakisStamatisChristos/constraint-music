"""Witness-based mutations for the preregistered multifixture-assurance-v1 corpus.

Eligibility and adjudication are determined before calling production checkers.
No checker decision is used to select a witness or relabel an invalid case.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from mido import Message, MidiFile

from constraint_music.modulation_runtime import result_from_dict
from constraint_music.provenance import artifact_content_digest, artifact_payload

from .oracle.delivery import parse_midi_bytes


@dataclass(frozen=True)
class AppliedMutation:
    applicability: str
    reason: str
    payload: dict[str, Any]
    midi: bytes
    witness: dict[str, Any]


def _tracks(profile: str) -> tuple[str, ...]:
    return ("Soprano", "Alto", "Tenor", "Bass") + (
        ("Melody",) if profile == "melody-plus-satb" else ()
    )


def _projection(data: bytes, profile: str) -> object:
    parsed = parse_midi_bytes(data, allowed_tracks=_tracks(profile))
    return (parsed.ticks_per_beat, parsed.note_events, parsed.context_events, parsed.issues)


def apply_mutation(
    definition: dict[str, Any], payload: dict[str, Any], data: bytes, profile: str
) -> AppliedMutation:
    """Apply one obligation violation or explicitly retain the ineligible slot."""
    changed = deepcopy(payload)
    music = changed["music"]
    eligibility = definition["eligibility"]
    field = {"target": "tonicization_targets", "modal": "modal_sources"}.get(eligibility)
    index = 0
    if field is not None:
        indices = [i for i, value in enumerate(music[field]) if value is not None]
        if not indices:
            return AppliedMutation(
                "NOT_APPLICABLE", f"no actual {field} witness", payload, data, {}
            )
        index = indices[0]
    if eligibility == "modulation" and not payload["spec"]["modulation_enabled"]:
        return AppliedMutation(
            "NOT_APPLICABLE", "persistent modulation disabled", payload, data, {}
        )
    if eligibility == "rhythm" and not payload["spec"]["rhythm_enabled"]:
        return AppliedMutation("NOT_APPLICABLE", "rhythm disabled", payload, data, {})
    if eligibility.startswith("melody"):
        if profile != "melody-plus-satb":
            return AppliedMutation(
                "NOT_APPLICABLE", "profile does not certify melody events", payload, data, {}
            )
        state = {"melody-rest": "rest", "melody-tie": "tie"}.get(eligibility)
        if state is not None:
            indices = [i for i, value in enumerate(music["rhythm"]) if value == state]
            if not indices:
                return AppliedMutation(
                    "NOT_APPLICABLE", f"no actual {state} witness", payload, data, {}
                )
            index = indices[0]

    mutation = definition["id"]
    witness: dict[str, Any] = {"obligation": definition["obligation"]}
    updated_data = data
    field = None
    if mutation == "missing-tenor":
        field = "tenor_midi"
        original = music.pop(field)
        witness.update(path=f"music.{field}", before=original, after="<missing>")
    elif mutation == "music-nonobject":
        witness.update(path="music", before_type="object", after_type="array")
        changed["music"] = []
    elif mutation in {
        "soprano-register",
        "bass-register",
        "initial-tie",
        "degree-boolean",
        "remove-target",
        "swap-modal-source",
        "display-name",
    }:
        field = {
            "soprano-register": "soprano_midi",
            "bass-register": "bass_midi",
            "initial-tie": "rhythm",
            "degree-boolean": "chord_degrees",
            "remove-target": "tonicization_targets",
            "swap-modal-source": "modal_sources",
            "display-name": "chord_form_names",
        }[mutation]
        before = music[field][index]
        after: object
        if mutation == "soprano-register":
            after = 100  # Outside the fixed SATB soprano register, within MIDI domain.
        elif mutation == "bass-register":
            after = payload["spec"]["bass_low"] - 1
        elif mutation == "initial-tie":
            after = "tie"
        elif mutation == "degree-boolean":
            after = True
        elif mutation == "remove-target":
            after = None
        elif mutation == "swap-modal-source":
            after = (
                "parallel_major" if before == "parallel_natural_minor" else "parallel_natural_minor"
            )
        else:
            after = "forged-form"
        music[field][index] = after
        witness.update(path=f"music.{field}[{index}]", index=index, before=before, after=after)
    elif mutation == "stale-context":
        index = payload["spec"]["modulation_boundary_beat"]
        before = music["key_contexts"][index]
        after = deepcopy(music["key_contexts"][0])
        music["key_contexts"][index] = after
        witness.update(path=f"music.key_contexts[{index}]", index=index, before=before, after=after)
    elif mutation in {"contract-version", "empty-rules", "composition-digest"}:
        field = {
            "contract-version": "constraint_contract_version",
            "empty-rules": "verified_constraint_ids",
            "composition-digest": "composition_sha256",
        }[mutation]
        before = changed["provenance"][field]
        after = (
            []
            if mutation == "empty-rules"
            else ("unsupported-contract" if mutation == "contract-version" else "0" * 64)
        )
        changed["provenance"][field] = after
        witness.update(path=f"provenance.{field}", before=before, after=after)
    elif mutation == "objective-vector":
        vector = changed["search"]["objective_vector"]
        before = vector["tension_deviation"]
        vector["tension_deviation"] += 1
        witness.update(
            path="search.objective_vector.tension_deviation", before=before, after=before + 1
        )
    elif mutation == "embedded-seed":
        before = changed["spec"]["seed"]
        changed["spec"]["seed"] += 1
        changed = artifact_payload(result_from_dict(changed))
        witness.update(
            path="spec.seed",
            before=before,
            after=before + 1,
            coordinated="embedded request, composition, content hashes and metadata",
            externally_expected_seed=before,
        )
    elif definition["family"] == "delivery":
        midi = MidiFile(file=BytesIO(data))
        if mutation == "soprano-channel":
            track = next(t for t in midi.tracks if t.name == "Soprano")
            for message in track:
                if message.type in {"note_on", "note_off"}:
                    message.channel = 5
            witness.update(
                path="Soprano.channel",
                before=0,
                after=5,
                coordinated="both ends of each note preserve pairing",
            )
        elif mutation == "missing-track":
            track = next(t for t in midi.tracks if t.name == "Tenor")
            midi.tracks.remove(track)
            witness.update(path="tracks.Tenor", before="present", after="missing")
        elif mutation == "duplicate-track":
            track = next(t for t in midi.tracks if t.name == "Soprano")
            midi.tracks.append(deepcopy(track))
            witness.update(path="tracks.Soprano", before=1, after=2)
        elif mutation == "wrong-key":
            event = next(m for t in midi.tracks for m in t if m.type == "key_signature")
            before = event.key
            event.key = "G" if before == "C" else "C"
            witness.update(path="initial key signature", before=before, after=event.key)
        elif mutation == "wrong-division":
            before = midi.ticks_per_beat
            midi.ticks_per_beat *= 2
            witness.update(path="ticks_per_beat", before=before, after=midi.ticks_per_beat)
        elif mutation in {"melody-onset", "fill-rest", "shorten-tie"}:
            track = next(t for t in midi.tracks if t.name == "Melody")
            step_ticks = 480 // payload["spec"]["subdivisions_per_beat"]
            if mutation == "melody-onset":
                message = next(m for m in track if m.type == "note_on" and m.velocity)
                before = message.time
                message.time += 1
                witness.update(path="first melody note-on delta", before=before, after=message.time)
            elif mutation == "fill-rest":
                # Absolute event insertion preserves the onset of every preexisting event.
                onset = index * step_ticks
                absolute = 0
                events = []
                for position, message in enumerate(track):
                    absolute += message.time
                    events.append((absolute, position, message.copy(time=0)))
                pitch = music["melody_midi"][index]
                events.extend(
                    [
                        (onset, -1, Message("note_on", channel=4, note=pitch, velocity=80)),
                        (onset + step_ticks, -1, Message("note_off", channel=4, note=pitch)),
                    ]
                )
                previous = 0
                track.clear()
                for tick, _order, message in sorted(events, key=lambda value: value[:2]):
                    track.append(message.copy(time=tick - previous))
                    previous = tick
                witness.update(
                    path="Melody rest interval",
                    index=index,
                    before="silence",
                    after={"pitch": pitch, "onset_tick": onset, "duration_ticks": step_ticks},
                )
            else:
                onset_index = index - 1
                while onset_index > 0 and music["rhythm"][onset_index] == "tie":
                    onset_index -= 1
                absolute = 0
                found = False
                for position, message in enumerate(track):
                    absolute += message.time
                    if message.type == "note_off" and absolute == (index + 1) * step_ticks:
                        # max_tie_steps=1 in the frozen matrix; leave later absolute ticks fixed.
                        if message.time <= 1:
                            raise ValueError("tie note-off delta cannot be shortened")
                        message.time -= 1
                        track[position + 1].time += 1
                        witness.update(
                            path="Melody tied note duration",
                            index=index,
                            before=(index + 1 - onset_index) * step_ticks,
                            after=(index + 1 - onset_index) * step_ticks - 1,
                        )
                        found = True
                        break
                if not found:
                    raise ValueError("eligible tie has no matching MIDI note-off")
        else:
            raise ValueError(f"Unknown delivery mutation {mutation}")
        output = BytesIO()
        midi.save(file=output)
        updated_data = output.getvalue()
        if _projection(data, profile) == _projection(updated_data, profile):
            raise ValueError("no-op MIDI event projection")
    else:
        raise ValueError(f"Unknown mutation {mutation}")

    if definition["tier"] == "repaired-digest":
        changed["provenance"]["artifact_content_sha256"] = artifact_content_digest(changed)
    if definition["family"] != "delivery" and artifact_content_digest(
        changed
    ) == artifact_content_digest(payload):
        raise ValueError("no-op artifact mutation")
    if definition["family"] == "delivery" and changed != payload:
        raise ValueError("delivery mutation changed the accepted artifact")
    return AppliedMutation(
        "APPLIED",
        "invalid by predeclared obligation; not checker-selected",
        changed,
        updated_data,
        witness,
    )
