"""Utilities to ensure Alembic always finds the migration scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MIGRATIONS_PATH = _PROJECT_ROOT / "migrations"


def _ensure_script_location(config: Any) -> None:
    """Ensure Alembic configurations always know where migrations live."""
    try:
        script_location = config.get_main_option("script_location")
    except Exception:
        return
    if script_location:
        return
    if not _MIGRATIONS_PATH.exists():
        return
    config.set_main_option("script_location", str(_MIGRATIONS_PATH))
    if not config.get_main_option("prepend_sys_path"):
        config.set_main_option("prepend_sys_path", str(_PROJECT_ROOT))


try:  # pragma: no cover - optional dependency during import
    from alembic.config import Config as AlembicConfig
except Exception:  # pragma: no cover - Alembic might not be installed
    AlembicConfig = None  # type: ignore[assignment]
else:
    if not getattr(AlembicConfig, "_ged_patched", False):
        _original_init = AlembicConfig.__init__

        def _patched_init(self, *args: Any, **kwargs: Any) -> None:
            _original_init(self, *args, **kwargs)
            _ensure_script_location(self)

        AlembicConfig.__init__ = _patched_init  # type: ignore[assignment]
        AlembicConfig._ged_patched = True  # type: ignore[attr-defined]

__all__ = []
