"""Functional, lightweight audio-to-MIDI pipeline used by the local milestone.

This deliberately extracts a dominant-pitch arrangement. It is useful and deterministic,
but does not claim note-perfect polyphonic transcription. Model-backed transcribers can
replace it through the contracts module.
"""

from dataclasses import dataclass
from pathlib import Path

import mido
import numpy as np
import soundfile as sf
from scipy.io import wavfile
from scipy.signal import resample_poly

from .models import AudioAnalysis, ProcessingParameters


@dataclass(slots=True)
class Note:
    pitch: int
    start: float
    end: float
    velocity: int


KEY_NAMES = ("C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B")


def _load_audio(path: Path, target_rate: int = 22_050) -> tuple[np.ndarray, int]:
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    audio = np.mean(audio, axis=1)
    if sample_rate != target_rate:
        divisor = int(np.gcd(sample_rate, target_rate))
        audio = resample_poly(audio, target_rate // divisor, sample_rate // divisor)
    return np.asarray(audio, dtype=np.float32), target_rate


def _frames(audio: np.ndarray, size: int = 2048, hop: int = 512) -> np.ndarray:
    if audio.size < size:
        audio = np.pad(audio, (0, size - audio.size))
    count = 1 + (audio.size - size) // hop
    return np.lib.stride_tricks.sliding_window_view(audio, size)[::hop][:count]


def _estimate_tempo(audio: np.ndarray, sample_rate: int) -> float:
    hop = 512
    framed = _frames(audio, hop=hop)
    energy = np.sqrt(np.mean(framed * framed, axis=1))
    onset = np.maximum(0, np.diff(energy, prepend=energy[0]))
    onset -= np.mean(onset)
    correlation = np.correlate(onset, onset, mode="full")[onset.size - 1 :]
    minimum_lag = max(1, round(60 * sample_rate / hop / 220))
    maximum_lag = min(correlation.size, round(60 * sample_rate / hop / 40))
    if maximum_lag <= minimum_lag or np.max(correlation[minimum_lag:maximum_lag]) <= 1e-9:
        return 120.0
    lag = minimum_lag + int(np.argmax(correlation[minimum_lag:maximum_lag]))
    return float(np.clip(60 * sample_rate / hop / lag, 40, 220))


def _chroma_profile(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    framed = _frames(audio) * np.hanning(2048)
    spectrum = np.abs(np.fft.rfft(framed, axis=1))
    frequencies = np.fft.rfftfreq(2048, 1 / sample_rate)
    valid = frequencies >= 32.7
    midi = np.rint(69 + 12 * np.log2(frequencies[valid] / 440)).astype(int)
    profile = np.zeros(12)
    for pitch_class in range(12):
        profile[pitch_class] = float(np.sum(spectrum[:, valid][:, midi % 12 == pitch_class]))
    return profile


def analyze_audio(path: Path) -> tuple[AudioAnalysis, np.ndarray, int]:
    audio, sample_rate = _load_audio(path)
    if audio.size == 0:
        raise ValueError("Decoded audio is empty")
    bpm = _estimate_tempo(audio, sample_rate)
    profile = _chroma_profile(audio, sample_rate)
    tonic = int(np.argmax(profile))
    confidence = float(profile[tonic] / max(float(np.sum(profile)), 1e-9))
    analysis = AudioAnalysis(
        duration_seconds=float(audio.size / sample_rate),
        bpm=round(bpm, 2),
        key=f"{KEY_NAMES[tonic]} major/minor",
        confidence=round(min(confidence * 4, 1.0), 3),
    )
    return analysis, audio, sample_rate


def transcribe_dominant_pitch(audio: np.ndarray, sample_rate: int, bpm: float) -> list[Note]:
    hop = 512
    framed = _frames(audio, hop=hop)
    windowed = framed * np.hanning(framed.shape[1])
    magnitudes = np.abs(np.fft.rfft(windowed, axis=1))
    frequencies = np.fft.rfftfreq(framed.shape[1], 1 / sample_rate)
    allowed = (frequencies >= 65.4) & (frequencies <= 2093)
    selected = magnitudes[:, allowed]
    peak_bins = np.argmax(selected, axis=1)
    peak_strength = selected[np.arange(selected.shape[0]), peak_bins]
    peak_frequency = frequencies[allowed][peak_bins]
    midi_pitch = np.rint(69 + 12 * np.log2(peak_frequency / 440)).astype(int)
    rms = np.sqrt(np.mean(framed * framed, axis=1))
    voiced = rms > max(float(np.max(rms)) * 0.08, 1e-5)
    boundaries = [0]
    for index in range(1, len(midi_pitch)):
        if (
            voiced[index] != voiced[index - 1]
            or abs(midi_pitch[index] - midi_pitch[index - 1]) >= 1
        ):
            boundaries.append(index)
    boundaries.append(len(midi_pitch))
    minimum = 60.0 / bpm / 8.0
    notes: list[Note] = []
    for left, right in zip(boundaries, boundaries[1:], strict=False):
        if right <= left:
            continue
        if not np.any(voiced[left:right]):
            continue
        pitch = int(np.clip(round(float(np.median(midi_pitch[left:right]))), 36, 96))
        strength = float(np.max(peak_strength[left:right]))
        start = left * hop / sample_rate
        end = min(audio.size / sample_rate, (right * hop + framed.shape[1]) / sample_rate)
        if end - start < minimum:
            continue
        velocity = int(
            np.clip(55 + 45 * strength / max(float(np.max(peak_strength)), 1e-9), 45, 105)
        )
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
