"""Command line interface for the ingest pipeline."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from .approve import approve_candidates
from .fetch import fetch_pages
from .fetch_http import (
    DEFAULT_LIMIT,
    DEFAULT_MAX_DELAY,
    DEFAULT_MIN_DELAY,
    DEFAULT_TIMEOUT,
    DEFAULT_USER_AGENT,
    fetch_http_pages,
)
from .normalize import normalize_candidates
from .parse import parse_pages

logger = logging.getLogger(__name__)


def _str_to_bool(value: str) -> bool:
    lowered = value.lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    msg = f"Invalid boolean value: {value}"
    raise argparse.ArgumentTypeError(msg)


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

    fetch_http_parser = subparsers.add_parser(
        "fetch-http",
        help="Fetch pages for a source using HTTP",
    )
    fetch_http_parser.add_argument("--source", required=True, help="Source identifier")
    fetch_http_parser.add_argument("--pref", required=True, help="Prefecture slug")
    fetch_http_parser.add_argument("--city", required=True, help="City slug")
    fetch_http_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Number of detail pages to fetch (1-30)",
    )
    fetch_http_parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help="Minimum delay between requests in seconds",
    )
    fetch_http_parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help="Maximum delay between requests in seconds",
    )
    fetch_http_parser.add_argument(
        "--respect-robots",
        type=_str_to_bool,
        default=True,
        help="Whether to respect robots.txt",
    )
    fetch_http_parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header to use",
    )
    fetch_http_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Request timeout in seconds",
    )
    fetch_http_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List URLs without fetching detail pages",
    )
    fetch_http_parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore conditional headers and force re-fetch",
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
    normalize_parser.add_argument(
        "--geocode-missing",
        action="store_true",
        help="Also geocode candidates lacking coordinates",
    )

    approve_parser = subparsers.add_parser("approve", help="Approve one or more gym candidates")
    approve_parser.add_argument(
        "--candidate-id",
        dest="candidate_ids",
        action="append",
        required=True,
        type=int,
        help="Candidate identifier to approve (repeatable)",
    )
    approve_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run approval without mutating the database",
    )

    batch_parser = subparsers.add_parser(
        "batch",
        help="Run full batch pipeline: fetch-http -> parse -> normalize -> diff -> approve",
    )
    batch_parser.add_argument("--source", required=True, help="Source identifier")
    batch_parser.add_argument("--pref", required=True, help="Prefecture slug")
    batch_parser.add_argument("--city", required=True, help="City slug")
    batch_parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Max number of detail pages to fetch (passes to fetch-http)",
    )
    batch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute pipeline without mutating database (approve phase skipped)",
    )
    batch_parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Override retry attempts for network phases",
    )
    batch_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="Timeout per HTTP request (fetch-http)",
    )
    batch_parser.add_argument(
        "--min-delay",
        type=float,
        default=DEFAULT_MIN_DELAY,
        help="Minimum delay between HTTP requests",
    )
    batch_parser.add_argument(
        "--max-delay",
        type=float,
        default=DEFAULT_MAX_DELAY,
        help="Maximum delay between HTTP requests",
    )
    batch_parser.add_argument(
        "--respect-robots",
        type=_str_to_bool,
        default=True,
        help="Whether to respect robots.txt (fetch-http)",
    )
    batch_parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User-Agent header to use (fetch-http)",
    )
    batch_parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-fetch ignoring conditional headers",
    )

    return parser


async def _run_async_command(func: Callable[..., Awaitable[int]], *args, **kwargs) -> int:
    return await func(*args, **kwargs)


def _dispatch(args: argparse.Namespace) -> int:
    command = args.command
    if command == "fetch":
        return asyncio.run(_run_async_command(fetch_pages, args.source, args.limit, args.file))
    if command == "fetch-http":
        return asyncio.run(
            _run_async_command(
                fetch_http_pages,
                args.source,
                pref=args.pref,
                city=args.city,
                limit=args.limit,
                min_delay=args.min_delay,
                max_delay=args.max_delay,
                respect_robots=args.respect_robots,
                user_agent=args.user_agent,
                timeout=args.timeout,
                dry_run=args.dry_run,
                force=args.force,
            )
        )
    if command == "parse":
        return asyncio.run(_run_async_command(parse_pages, args.source, args.limit))
    if command == "normalize":
        return asyncio.run(
            _run_async_command(
                normalize_candidates,
                args.source,
                args.limit,
                geocode_missing=args.geocode_missing,
            )
        )
    if command == "approve":
        return asyncio.run(_run_async_command(approve_candidates, args.candidate_ids, args.dry_run))
    if command == "batch":
        # Lazy import to keep CLI lightweight for other commands.
        from .pipeline import (
            run_batch,  # noqa: PLC0415 (local import for optional dependency handling)
        )

        return asyncio.run(
            _run_async_command(
                run_batch,
                source=args.source,
                pref=args.pref,
                city=args.city,
                limit=args.limit,
                dry_run=args.dry_run,
                max_retries=args.max_retries,
                timeout=args.timeout,
                min_delay=args.min_delay,
                max_delay=args.max_delay,
                respect_robots=args.respect_robots,
                user_agent=args.user_agent,
                force=args.force,
            )
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
