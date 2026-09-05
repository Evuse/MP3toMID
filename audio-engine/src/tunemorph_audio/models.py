from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AudioAnalysis:
    duration_seconds: float
    bpm: float
    key: str
    confidence: float
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProcessingParameters:
    fidelity: int = 75
    complexity: int = 50
    quantization: str = "1/16"
    transpose: int = 0
    humanize: int = 10
    max_polyphony: int = 6
    preserve_melody: bool = True
    include_drums: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StemSet:
    vocals: Path | None = None
    drums: Path | None = None
    bass: Path | None = None
    other: Path | None = None


@dataclass(frozen=True, slots=True)
class MidiArtifact:
    path: Path
    note_count: int


@dataclass(frozen=True, slots=True)
class StyledMidi:
    artifact: MidiArtifact
    style_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
