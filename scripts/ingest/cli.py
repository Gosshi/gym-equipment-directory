"""Command line interface for the ingest pipeline."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Sequence

from .approve import approve_candidate
from .fetch import fetch_pages
from .normalize import normalize_candidates
from .parse import parse_pages

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest pipeline utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch pages for a source")
    fetch_parser.add_argument("--source", required=True, help="Source identifier")
    fetch_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of items to process",
    )
    fetch_parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Path to a file that contains URLs (one per line)",
    )

    parse_parser = subparsers.add_parser("parse", help="Parse scraped pages into candidates")
    parse_parser.add_argument("--source", required=True, help="Source identifier")
    parse_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of items to process",
    )

    normalize_parser = subparsers.add_parser(
        "normalize", help="Normalize parsed gym candidate records"
    )
    normalize_parser.add_argument("--source", required=True, help="Source identifier")
    normalize_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Number of items to process",
    )

    approve_parser = subparsers.add_parser(
        "approve", help="Approve a gym candidate (dummy implementation)"
    )
    approve_parser.add_argument(
        "--candidate-id",
        required=True,
        type=int,
        help="Candidate identifier to approve",
    )
    approve_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run approval without mutating the database",
    )

    return parser


async def _run_async_command(
    func: Callable[..., Awaitable[int]], *args, **kwargs
) -> int:
    return await func(*args, **kwargs)


def _dispatch(args: argparse.Namespace) -> int:
    command = args.command
    if command == "fetch":
        return asyncio.run(_run_async_command(fetch_pages, args.source, args.limit, args.file))
    if command == "parse":
        return asyncio.run(_run_async_command(parse_pages, args.source, args.limit))
    if command == "normalize":
        return asyncio.run(_run_async_command(normalize_candidates, args.source, args.limit))
    if command == "approve":
        return asyncio.run(
            _run_async_command(approve_candidate, args.candidate_id, args.dry_run)
        )
    msg = f"Unknown command: {command}"
    raise ValueError(msg)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _dispatch(args)
    except Exception:  # pragma: no cover - CLI entry point safeguard
        logger.exception("Ingest command failed")
        return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
