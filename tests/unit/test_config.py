import os

from src.core.config import Settings


def test_log_level_accepts_empty_string_and_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("INNOVASOFT_BASE_URL", os.environ["INNOVASOFT_BASE_URL"])
    monkeypatch.setenv("MONGODB_URI", os.environ["MONGODB_URI"])
    monkeypatch.setenv("MONGODB_DATABASE", os.environ["MONGODB_DATABASE"])
    monkeypatch.setenv("LOG_LEVEL", "")

    settings = Settings()

    assert settings.log_level == "INFO"


def test_request_log_ttl_seconds_accepts_empty_string(monkeypatch):
    monkeypatch.setenv("INNOVASOFT_BASE_URL", os.environ["INNOVASOFT_BASE_URL"])
    monkeypatch.setenv("MONGODB_URI", os.environ["MONGODB_URI"])
    monkeypatch.setenv("MONGODB_DATABASE", os.environ["MONGODB_DATABASE"])
    monkeypatch.setenv("REQUEST_LOG_TTL_SECONDS", "")

    settings = Settings()

    assert settings.request_log_ttl_seconds is None
