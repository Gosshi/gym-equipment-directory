"""Utility functions for loading municipal parser configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

_CONFIG_CACHE: dict[str, dict[str, Any]] = {}
_CONFIG_DIR = Path(__file__).resolve().parents[4] / "configs" / "municipal"


def load_config(ward: str) -> dict[str, Any]:
    """Load configuration YAML for the given *ward* identifier."""

    if ward in _CONFIG_CACHE:
        return dict(_CONFIG_CACHE[ward])

    path = _CONFIG_DIR / f"{ward}.yaml"
    if not path.exists():
        msg = f"Municipal parser config not found: {path}"
        raise FileNotFoundError(msg)

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        msg = f"Invalid municipal parser config structure for ward '{ward}'"
        raise ValueError(msg)

    _CONFIG_CACHE[ward] = data
    return dict(data)


__all__ = ["load_config"]
