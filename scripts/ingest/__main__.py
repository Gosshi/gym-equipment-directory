"""Module entrypoint for ``python -m scripts.ingest``."""

from .cli import main

if __name__ == "__main__":  # pragma: no cover - CLI dispatch
    raise SystemExit(main())
