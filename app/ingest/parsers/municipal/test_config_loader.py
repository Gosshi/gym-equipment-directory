from pathlib import Path

from app.ingest.parsers.municipal import config_loader


def test_load_config_uses_packaged_resource(monkeypatch):
    monkeypatch.setattr(config_loader, "_CONFIG_CACHE", {})
    monkeypatch.setattr(config_loader, "_CONFIG_DIR", Path("/non-existent"))

    data = config_loader.load_config("municipal_koto")

    assert data
    assert data["start_urls"]
