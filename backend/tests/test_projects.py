import io
import wave

from fastapi.testclient import TestClient
from tunemorph_backend.config import get_settings
from tunemorph_backend.main import app


def wav_bytes(duration: float = 0.1, sample_rate: int = 8_000) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(b"\0\0" * int(duration * sample_rate))
    return output.getvalue()


def test_project_upload_and_delete() -> None:
    with TestClient(app) as client:
        created = client.post("/api/projects", json={"style": "music_box"})
        assert created.status_code == 201
        project_id = created.json()["id"]

        uploaded = client.post(
            f"/api/projects/{project_id}/audio",
            files={"audio": ("../../melody.wav", wav_bytes(), "audio/wav")},
        )
        assert uploaded.status_code == 200, uploaded.text
        body = uploaded.json()
        assert body["original_filename"] == "melody.wav"
        assert 0.09 < body["audio_file"]["duration_seconds"] < 0.11

        source = get_settings().data_dir / "projects" / project_id / "source" / "audio.wav"
        assert source.is_file()
        assert (source.parents[1] / "metadata.json").is_file()

        playback = client.get(f"/api/projects/{project_id}/audio")
        assert playback.status_code == 200
        assert playback.headers["content-type"].startswith("audio/wav")
        assert playback.content == wav_bytes()

        status = client.get(f"/api/projects/{project_id}/status")
        assert status.json()["status"] == "pending"
        assert client.delete(f"/api/projects/{project_id}").status_code == 204
        assert not source.parents[1].exists()


def test_rejects_mime_mismatch_and_corrupt_wav() -> None:
    with TestClient(app) as client:
        first = client.post("/api/projects", json={}).json()["id"]
        mismatch = client.post(
            f"/api/projects/{first}/audio",
            files={"audio": ("track.wav", wav_bytes(), "application/octet-stream")},
        )
        assert mismatch.status_code == 415

        second = client.post("/api/projects", json={}).json()["id"]
        corrupt = client.post(
            f"/api/projects/{second}/audio",
            files={"audio": ("track.wav", b"not audio", "audio/wav")},
        )
        assert corrupt.status_code == 422
        assert not (get_settings().data_dir / "projects" / second / "source" / "audio.wav").exists()


def test_unknown_style_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post("/api/projects", json={"style": "unknown"})
    assert response.status_code == 422
