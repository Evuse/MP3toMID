from abc import ABC, abstractmethod
from pathlib import Path

from .models import AudioAnalysis, MidiArtifact, ProcessingParameters, StemSet, StyledMidi


class SourceSeparator(ABC):
    @abstractmethod
    async def separate(self, audio_path: Path, output_dir: Path) -> StemSet:
        """Separate audio into available semantic stems."""


class AudioTranscriber(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: Path, output_path: Path) -> MidiArtifact:
        """Derive pitched and rhythmic MIDI events from decoded audio."""


class TempoDetector(ABC):
    @abstractmethod
    async def detect(self, audio_path: Path) -> tuple[float, float]:
        """Return BPM and confidence in the inclusive range zero to one."""


class KeyDetector(ABC):
    @abstractmethod
    async def detect(self, audio_path: Path) -> tuple[str, float]:
        """Return musical key label and confidence."""


class MidiPostProcessor(ABC):
    @abstractmethod
    async def process(self, midi: MidiArtifact, parameters: ProcessingParameters) -> MidiArtifact:
        """Clean, quantize and constrain a transcription."""


class StyleTransformer(ABC):
    style_id: str

    @abstractmethod
    async def transform(
        self,
        midi: MidiArtifact,
        analysis: AudioAnalysis,
        parameters: ProcessingParameters,
    ) -> StyledMidi:
        """Create a musically altered arrangement, not just a program change."""


class PreviewRenderer(ABC):
    @abstractmethod
    async def render(self, midi: StyledMidi, output_path: Path) -> Path:
        """Render a MIDI arrangement to an audio preview."""
