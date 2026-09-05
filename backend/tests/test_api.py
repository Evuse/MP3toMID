from fastapi.testclient import TestClient
from tunemorph_backend.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_styles_are_available() -> None:
    with TestClient(app) as client:
        response = client.get("/api/styles")
    assert response.status_code == 200
    assert {style["id"] for style in response.json()} == {
        "original",
        "music_box",
        "solo_piano",
        "eight_bit",
        "lullaby",
    }


def test_unknown_style_is_404() -> None:
    with TestClient(app) as client:
        response = client.get("/api/styles/nope")
    assert response.status_code == 404
