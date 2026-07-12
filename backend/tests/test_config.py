from app.config import Settings


def test_cors_origins_accept_comma_separated_environment(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.test,http://localhost:8080")
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["https://app.example.test", "http://localhost:8080"]

