"""Command line interface. Exit codes: 0 ok, 1 completed with rejected/failed records, 2 could not run."""

import argparse
import asyncio
import json
import sys
import uuid
from typing import List, Optional

from sqlalchemy import select

from . import runner
from .sources import demo_fixtures, github_repos, manual_posts


def _print_summary(summary: runner.RunSummary, as_json: bool) -> None:
    counts = summary.counts()
    if as_json:
        print(json.dumps({
            "run_id": summary.run_id, "source_type": summary.source_type, "dry_run": summary.dry_run,
            "counts": counts,
            "results": [{"status": r.status, "entity": r.entity, "id": str(r.entity_id) if r.entity_id else None,
                         "code": r.code, "message": r.message} for r in summary.results],
        }, indent=2))
        return
    mode = "DRY RUN (nothing written)" if summary.dry_run else f"run {summary.run_id}"
    print(f"{summary.source_type}: {mode}")
    for i, r in enumerate(summary.results):
        extra = f" [{r.code}] {r.message}" if r.code or r.message else ""
        print(f"  #{i:<3} {r.status:<10} {r.entity:<11}{extra}")
    print("  summary: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


def _exit_code(summary: runner.RunSummary) -> int:
    c = summary.counts()
    return 1 if c["rejected"] or c["failed"] else 0


async def _runs(limit: int) -> None:
    from app.shared.database import AsyncSessionLocal
    from app.shared.ingestion_log import IngestionRun

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(limit))).scalars().all()
    if not rows:
        print("no ingestion runs recorded")
    for r in rows:
        print(f"{r.id}  {r.started_at:%Y-%m-%d %H:%M:%S}  {r.source_type:<13} {r.status:<22} "
              f"seen={r.records_seen} created={r.records_created} updated={r.records_updated} "
              f"dup={r.records_duplicate} rejected={r.records_rejected} failed={r.records_failed}"
              f"{'  [demo]' if r.is_demo else ''}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ingest.py", description="Load real data into the Synapse database.")
    sub = p.add_subparsers(dest="cmd", required=True)

    posts = sub.add_parser("posts", help="ingest job posts you provide (JSON/JSONL/TXT file or --text)")
    posts.add_argument("--file", help=".json / .jsonl (records) or .txt (the whole file is one post)")
    posts.add_argument("--text", help="a single post's text")
    posts.add_argument("--platform", help="twitter|linkedin|reddit|telegram (required with --text or a .txt file)")
    posts.add_argument("--source-url", help="where the text came from, if known")
    posts.add_argument("--author-handle")
    posts.add_argument("--note", help="free-text provenance note stored with the post")

    gh = sub.add_parser("github", help="fetch repository metadata from the GitHub REST API")
    gh.add_argument("urls", nargs="*", help="https://github.com/<owner>/<repo> URLs")
    gh.add_argument("--file", help=".txt (one URL per line) or .json")
    gh.add_argument("--candidate-name", help="applies to every URL given on the command line")
    gh.add_argument("--target-role")

    demo = sub.add_parser("demo", help="labelled development fixtures (is_demo = true)")
    demo.add_argument("action", choices=["load", "remove"])

    runs = sub.add_parser("runs", help="list recent ingestion runs")
    runs.add_argument("--limit", type=int, default=10)

    rb = sub.add_parser("rollback", help="delete exactly the rows created by one run")
    rb.add_argument("--run", required=True, help="run id (see `runs`)")

    for sp in (posts, gh, demo):
        sp.add_argument("--dry-run", action="store_true", help="validate and report; write nothing")
    for sp in (posts, gh, demo, runs, rb):
        sp.add_argument("--json", action="store_true", help="machine-readable output")
    return p


async def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "posts":
        if args.file:
            items = manual_posts.from_file(
                args.file, platform=args.platform,
                **{k: v for k, v in (("source_url", args.source_url), ("author_handle", args.author_handle), ("note", args.note)) if v})
            label = args.file.rsplit("/", 1)[-1]
        elif args.text:
            if not args.platform:
                print("error: --platform is required with --text", file=sys.stderr)
                return 2
            items = manual_posts.from_text(
                args.text, args.platform,
                **{k: v for k, v in (("source_url", args.source_url), ("author_handle", args.author_handle), ("note", args.note)) if v})
            label = "--text"
        else:
            print("error: give --file or --text", file=sys.stderr)
            return 2
        summary = await runner.run_posts(items, source_type="manual_text", label=label, dry_run=args.dry_run)
    elif args.cmd == "github":
        items = []
        if args.file:
            items += github_repos.from_file(args.file)
        if args.urls:
            items += github_repos.from_urls(args.urls, candidate_name=args.candidate_name, target_role=args.target_role)
        if not items:
            print("error: give at least one URL or --file", file=sys.stderr)
            return 2
        summary = await runner.run_github(items, label=args.file or "cli", dry_run=args.dry_run)
    elif args.cmd == "demo":
        if args.action == "remove":
            out = await runner.remove_demo()
            print(json.dumps(out) if args.json else f"removed demo fixtures: {out}")
            return 0
        posts_summary = await runner.run_posts(demo_fixtures.posts(), source_type="demo_fixture", label="showcase.json",
                                               is_demo=True, dry_run=args.dry_run)
        repos_summary = await runner.run_demo_candidates(demo_fixtures.candidates(), dry_run=args.dry_run)
        _print_summary(posts_summary, args.json)
        _print_summary(repos_summary, args.json)
        return max(_exit_code(posts_summary), _exit_code(repos_summary))
    elif args.cmd == "runs":
        await _runs(args.limit)
        return 0
    elif args.cmd == "rollback":
        try:
            run_id = uuid.UUID(args.run)
        except ValueError:
            print("error: --run must be a UUID", file=sys.stderr)
            return 2
        out = await runner.rollback_run(run_id)
        print(json.dumps(out) if args.json else f"rolled back run {run_id}: {out}")
        return 0
    else:  # pragma: no cover
        return 2

    _print_summary(summary, args.json)
    return _exit_code(summary)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(_dispatch(args))
    except runner.IngestionAborted as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc}", file=sys.stderr)
        return 2
