from tunemorph_backend.config import Settings


def test_plain_comma_separated_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    settings = Settings(_env_file=None)
    assert settings.backend_cors_origins == (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    )
