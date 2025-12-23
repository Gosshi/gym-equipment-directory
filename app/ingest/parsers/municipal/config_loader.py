"""Utility functions for loading municipal parser configuration."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from scripts.ingest.sources_registry import GLOBAL_ARTICLE_PATTERNS

_CONFIG_CACHE: dict[str, dict[str, Any]] = {}
_CONFIG_DIR = Path(__file__).resolve().parents[4] / "configs" / "municipal"


def _load_from_filesystem(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        msg = f"Invalid municipal parser config structure for '{path.name}'"
        raise ValueError(msg)

    return data


def _load_from_package(ward: str) -> dict[str, Any] | None:
    try:
        resource = resources.files("configs.municipal").joinpath(f"{ward}.yaml")
    except ModuleNotFoundError:
        return None

    if not resource.is_file():
        return None

    with resource.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        msg = f"Invalid municipal parser config structure for ward '{ward}'"
        raise ValueError(msg)

    return data


def load_config(ward: str) -> dict[str, Any]:
    """Load configuration YAML for the given *ward* identifier."""

    if ward in _CONFIG_CACHE:
        return dict(_CONFIG_CACHE[ward])

    path = _CONFIG_DIR / f"{ward}.yaml"
    data = _load_from_filesystem(path)
    if data is None:
        data = _load_from_package(ward)
    if data is None:
        msg = f"Municipal parser config not found: {path}"
        raise FileNotFoundError(msg)

    # Universal Support: Inject global patterns into url_patterns
    if "url_patterns" in data and GLOBAL_ARTICLE_PATTERNS:
        patterns = data["url_patterns"]
        # Handle dict format (intro_top/detail_article)
        if isinstance(patterns, dict):
            current_detail = patterns.get("detail_article", "")
            current_intro = patterns.get("intro_top", "")

            # Construct OR regex
            global_regex = "|".join(GLOBAL_ARTICLE_PATTERNS)

            if current_detail:
                patterns["detail_article"] = f"{current_detail}|{global_regex}"
            else:
                patterns["detail_article"] = global_regex

            # Also add to intro if needed? Usually intro is just for crawling depth
            if current_intro:
                patterns["intro_top"] = f"{current_intro}|{global_regex}"
            else:
                patterns["intro_top"] = global_regex

    _CONFIG_CACHE[ward] = data
    return dict(data)


__all__ = ["load_config"]
