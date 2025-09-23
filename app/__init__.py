"""Application package initialization."""

# Ensure Alembic configurations are patched before tests set up databases.
from . import _alembic_config as _alembic_config_patch  # noqa: F401

__all__ = []
