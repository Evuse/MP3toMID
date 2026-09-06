import math
import wave
from pathlib import Path

import mido
from tunemorph_audio.models import ProcessingParameters
from tunemorph_audio.pipeline import (
    analyze_audio,
    render_preview,
    style_notes,
    transcribe_dominant_pitch,
    write_midi,
)


def write_tone(path: Path, frequency: float = 440, duration: float = 1.5) -> None:
    sample_rate = 8_000
    samples = bytearray()
    for index in range(int(sample_rate * duration)):
        value = int(12_000 * math.sin(2 * math.pi * frequency * index / sample_rate))
        samples.extend(value.to_bytes(2, "little", signed=True))
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(samples)


def test_tone_to_styled_midi_and_preview(tmp_path: Path) -> None:
    source = tmp_path / "tone.wav"
    midi_path = tmp_path / "music-box.mid"
    preview_path = tmp_path / "preview.wav"
    write_tone(source)

    analysis, audio, sample_rate = analyze_audio(source)
    raw = transcribe_dominant_pitch(audio, sample_rate, analysis.bpm)
    styled, program, factor = style_notes(
        raw,
        "music_box",
        analysis.bpm,
        ProcessingParameters(complexity=70, max_polyphony=4),
    )
    write_midi(styled, midi_path, analysis.bpm * factor, program)
    render_preview(styled, preview_path, analysis.duration_seconds, "music_box")

    parsed = mido.MidiFile(midi_path)
    assert any(message.type == "note_on" for track in parsed.tracks for message in track)
    assert midi_path.read_bytes().startswith(b"MThd")
    assert preview_path.read_bytes().startswith(b"RIFF")
    assert all(60 <= note.pitch <= 96 for note in styled)
