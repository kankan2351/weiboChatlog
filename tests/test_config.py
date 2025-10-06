import os
from pathlib import Path

import pytest

from chatbot.utils.config import Config


def test_config_provides_default_placeholders(monkeypatch, tmp_path):
    # Ensure all azure env values are absent so defaults are used
    for key in [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_KEY",
        "AZURE_EMBEDDING_ENDPOINT",
        "AZURE_EMBEDDING_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_API_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)

    log_dir = tmp_path / "logs"
    vector_db = tmp_path / "vector" / "db"
    sqlite_path = tmp_path / "sqlite" / "messages.db"
    config_dir = tmp_path / "config"

    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("VECTOR_DB_PATH", str(vector_db))
    monkeypatch.setenv("SQLITE_DB_PATH", str(sqlite_path))
    monkeypatch.setenv("CHATBOT_CONFIG_DIR", str(config_dir))

    config = Config()

    azure = config.get_azure_config()
    assert azure["openai_endpoint"].startswith("https://example")
    assert azure["openai_key"].startswith("dummy")
    assert azure["embedding_endpoint"].startswith("https://example")
    assert azure["embedding_key"].startswith("dummy")

    deepseek = config.get_deepseek_config()
    assert deepseek["base_url"].startswith("https://example")
    assert deepseek["api_key"].startswith("dummy")

    for path in [log_dir, vector_db.parent, sqlite_path.parent, config_dir]:
        assert path.exists()


def test_config_respects_environment_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://custom-endpoint")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "secret-key")
    monkeypatch.setenv("AZURE_EMBEDDING_ENDPOINT", "https://custom-embedding")
    monkeypatch.setenv("AZURE_EMBEDDING_KEY", "embedding-secret")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-secret")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("VECTOR_DB_PATH", str(tmp_path / "vector" / "db"))
    monkeypatch.setenv("SQLITE_DB_PATH", str(tmp_path / "sqlite" / "messages.db"))

    config = Config()

    azure = config.get_azure_config()
    assert azure["openai_endpoint"] == "https://custom-endpoint"
    assert azure["openai_key"] == "secret-key"
    assert azure["embedding_endpoint"] == "https://custom-embedding"
    assert azure["embedding_key"] == "embedding-secret"

    deepseek = config.get_deepseek_config()
    assert deepseek["base_url"] == "https://deepseek"
    assert deepseek["api_key"] == "deepseek-secret"

    assert config.is_development()
    monkeypatch.setenv("ENV", "production")
    config.load()
    assert config.is_production()
