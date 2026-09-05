import asyncio
import json
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path


class InvalidAudioError(ValueError):
    pass


@dataclass(frozen=True)
class ProbedAudio:
    duration_seconds: float


def _probe(path: Path) -> ProbedAudio:
    if path.suffix == ".wav":
        try:
            with wave.open(str(path), "rb") as source:
                duration = source.getnframes() / source.getframerate()
        except (wave.Error, EOFError, ZeroDivisionError) as error:
            raise InvalidAudioError("The WAV file cannot be decoded") from error
        return ProbedAudio(duration)

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise InvalidAudioError("ffprobe is required to validate this audio format")
    try:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration = float(json.loads(completed.stdout)["format"]["duration"])
    except (subprocess.SubprocessError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise InvalidAudioError("The audio file cannot be decoded") from error
    return ProbedAudio(duration)


async def probe_audio(path: Path) -> ProbedAudio:
    return await asyncio.to_thread(_probe, path)
