"""Functional, lightweight audio-to-MIDI pipeline used by the local milestone.

This deliberately extracts a dominant-pitch arrangement. It is useful and deterministic,
but does not claim note-perfect polyphonic transcription. Model-backed transcribers can
replace it through the contracts module.
"""

from dataclasses import dataclass
from pathlib import Path

import librosa
import mido
import numpy as np
from scipy.io import wavfile

from .models import AudioAnalysis, ProcessingParameters


@dataclass(slots=True)
class Note:
    pitch: int
    start: float
    end: float
    velocity: int


KEY_NAMES = ("C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B")


def analyze_audio(path: Path) -> tuple[AudioAnalysis, np.ndarray, int]:
    audio, sample_rate = librosa.load(path, sr=22_050, mono=True)
    if audio.size == 0:
        raise ValueError("Decoded audio is empty")
    tempo, _ = librosa.beat.beat_track(y=audio, sr=sample_rate)
    bpm = float(np.asarray(tempo).reshape(-1)[0]) if np.asarray(tempo).size else 120.0
    if not np.isfinite(bpm) or bpm <= 0:
        bpm = 120.0
    chroma = librosa.feature.chroma_cqt(y=audio, sr=sample_rate)
    profile = np.mean(chroma, axis=1)
    tonic = int(np.argmax(profile))
    confidence = float(profile[tonic] / max(float(np.sum(profile)), 1e-9))
    analysis = AudioAnalysis(
        duration_seconds=float(librosa.get_duration(y=audio, sr=sample_rate)),
        bpm=round(bpm, 2),
        key=f"{KEY_NAMES[tonic]} major/minor",
        confidence=round(min(confidence * 4, 1.0), 3),
    )
    return analysis, audio, sample_rate


def transcribe_dominant_pitch(audio: np.ndarray, sample_rate: int, bpm: float) -> list[Note]:
    hop = 512
    pitches, magnitudes = librosa.piptrack(
        y=audio,
        sr=sample_rate,
        hop_length=hop,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
    )
    onset_frames = librosa.onset.onset_detect(
        y=audio, sr=sample_rate, hop_length=hop, backtrack=True
    )
    boundaries = sorted({0, *map(int, onset_frames), pitches.shape[1]})
    minimum = 60.0 / bpm / 8.0
    notes: list[Note] = []
    for left, right in zip(boundaries, boundaries[1:], strict=False):
        if right <= left:
            continue
        region = magnitudes[:, left:right]
        flat_index = int(np.argmax(region))
        row, column = np.unravel_index(flat_index, region.shape)
        frequency = float(pitches[row, left + column])
        strength = float(region[row, column])
        if frequency <= 0 or strength < np.percentile(magnitudes, 70):
            continue
        start = float(librosa.frames_to_time(left, sr=sample_rate, hop_length=hop))
        end = float(librosa.frames_to_time(right, sr=sample_rate, hop_length=hop))
        if end - start < minimum:
            continue
        pitch = int(np.clip(round(librosa.hz_to_midi(frequency)), 36, 96))
        velocity = int(np.clip(55 + 45 * strength / max(float(np.max(magnitudes)), 1e-9), 45, 105))
        if notes and notes[-1].pitch == pitch and start - notes[-1].end < 0.04:
            notes[-1].end = end
        else:
            notes.append(Note(pitch, start, end, velocity))
    if not notes:
        raise ValueError("No stable pitched notes were detected in this audio")
    return notes


def _quantize(value: float, step: float) -> float:
    return round(value / step) * step if step else value


def style_notes(
    notes: list[Note], style: str, bpm: float, parameters: ProcessingParameters
) -> tuple[list[Note], int, float]:
    beat = 60.0 / bpm
    divisions = {"off": 0, "1/4": beat, "1/8": beat / 2, "1/16": beat / 4, "1/32": beat / 8}
    step = divisions.get(parameters.quantization, beat / 4)
    output: list[Note] = []
    keep_ratio = 0.3 + parameters.complexity / 140
    for index, source in enumerate(notes):
        if style != "original" and index / max(len(notes), 1) > keep_ratio and index % 2:
            continue
        pitch = int(np.clip(source.pitch + parameters.transpose, 21, 108))
        velocity = source.velocity
        start, end = _quantize(source.start, step), _quantize(source.end, step)
        program, tempo_factor = 0, 1.0
        if style == "music_box":
            while pitch < 60:
                pitch += 12
            while pitch > 96:
                pitch -= 12
            velocity = int(64 + parameters.fidelity * 0.08)
            end = min(end, start + beat * 0.75)
            program = 10
        elif style == "solo_piano":
            pitch = int(np.clip(pitch, 36, 96))
            program = 0
        elif style == "eight_bit":
            step = beat / 4
            start, end = _quantize(start, step), _quantize(end, step)
            velocity, program = 92, 80
        elif style == "lullaby":
            velocity, program, tempo_factor = min(velocity, 62), 8, 0.82
        if end <= start:
            end = start + max(step, 0.06)
        output.append(Note(pitch, start, end, velocity))
    return reduce_polyphony(output, parameters.max_polyphony), program, tempo_factor


def reduce_polyphony(notes: list[Note], limit: int) -> list[Note]:
    kept: list[Note] = []
    for note in sorted(notes, key=lambda item: (item.start, -item.pitch)):
        active = [item for item in kept if item.start <= note.start < item.end]
        if len(active) < max(1, limit):
            kept.append(note)
    return kept


def write_midi(notes: list[Note], path: Path, bpm: float, program: int) -> None:
    ticks = 480
    midi = mido.MidiFile(ticks_per_beat=ticks)
    track = mido.MidiTrack()
    midi.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    track.append(mido.Message("program_change", program=program, time=0))
    events: list[tuple[int, mido.Message]] = []
    seconds_per_tick = 60 / bpm / ticks
    for note in notes:
        start_tick = round(note.start / seconds_per_tick)
        end_tick = max(start_tick + 1, round(note.end / seconds_per_tick))
        events.append(
            (start_tick, mido.Message("note_on", note=note.pitch, velocity=note.velocity))
        )
        events.append((end_tick, mido.Message("note_off", note=note.pitch, velocity=0)))
    previous = 0
    for absolute, message in sorted(events, key=lambda item: (item[0], item[1].type == "note_on")):
        message.time = max(0, absolute - previous)
        track.append(message)
        previous = absolute
    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)


def render_preview(notes: list[Note], path: Path, duration: float, style: str) -> None:
    sample_rate = 22_050
    samples = np.zeros(int((duration + 0.5) * sample_rate), dtype=np.float32)
    for note in notes:
        left, right = int(note.start * sample_rate), min(int(note.end * sample_rate), samples.size)
        if right <= left:
            continue
        time = np.arange(right - left) / sample_rate
        frequency = 440.0 * 2 ** ((note.pitch - 69) / 12)
        envelope = np.exp(-time * (5.0 if style == "music_box" else 2.0))
        tone = np.sin(2 * np.pi * frequency * time)
        if style == "music_box":
            tone += 0.35 * np.sin(2 * np.pi * frequency * 2.01 * time)
        samples[left:right] += tone * envelope * (note.velocity / 127) * 0.18
    peak = float(np.max(np.abs(samples)))
    if peak:
        samples = samples / peak * 0.85
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, sample_rate, (samples * 32767).astype(np.int16))
