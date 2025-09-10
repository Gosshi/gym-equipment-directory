import importlib

import pytest


def test_weight_guard_ok(monkeypatch):
    monkeypatch.setenv("SCORE_W_FRESH", "0.6")
    monkeypatch.setenv("SCORE_W_RICH", "0.4")
    monkeypatch.setenv("FRESHNESS_WINDOW_DAYS", "365")
    # 遅延 import で main.create_app() を呼ぶ
    mod = importlib.import_module("app.main")
    assert mod.app  # 起動成功


def test_weight_guard_ng(monkeypatch):
    monkeypatch.setenv("SCORE_W_FRESH", "0.9")
    monkeypatch.setenv("SCORE_W_RICH", "0.2")
    with pytest.raises(Exception):
        importlib.reload(importlib.import_module("app.services.scoring"))
