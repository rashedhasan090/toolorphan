"""CLI entrypoint for toolorphan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from toolorphan import __version__
from toolorphan.diff import DiffResult, diff_tools
from toolorphan.jsonl_calls import load_call_counts
from toolorphan.manifest import load_manifest


def _format_text(result: DiffResult) -> str:
    lines: list[str] = []
    lines.append(
        f"declared={len(result.declared)}  called_unique={len(result.called)}  "
        f"matched={len(result.matched)}  orphans={len(result.orphans)}  "
        f"rogues={len(result.rogues)}  coverage={result.coverage:.0%}"
    )
    if result.matched:
        lines.append("")
        lines.append("Matched (declared + called):")
        for name, count in result.matched:
            lines.append(f"  {name}  ×{count}")
    if result.orphans:
        lines.append("")
        lines.append("Orphans (declared, never called):")
        for name in result.orphans:
            lines.append(f"  {name}")
    if result.rogues:
        lines.append("")
        lines.append("Rogues (called, never declared):")
        for name in result.rogues:
            lines.append(f"  {name}  ×{result.called[name]}")
    if not result.orphans and not result.rogues:
        lines.append("")
        lines.append("No orphans or rogues.")
    return "\n".join(lines) + "\n"


def _format_json(result: DiffResult) -> str:
    payload = {
        "declared": sorted(result.declared),
        "called": dict(sorted(result.called.items())),
        "matched": [{"name": n, "count": c} for n, c in result.matched],
        "orphans": result.orphans,
        "rogues": [{"name": n, "count": result.called[n]} for n in result.rogues],
        "coverage": round(result.coverage, 4),
        "orphan_ratio": round(result.orphan_ratio, 4),
    }
    return json.dumps(payload, indent=2) + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="toolorphan",
        description=(
            "Diff an agent tool manifest against tool-call JSONL logs. "
            "Report orphaned (declared never called) and rogue (called never declared) tools."
        ),
    )
    p.add_argument(
        "--manifest",
        "-m",
        required=True,
        type=Path,
        help="Path to tool manifest (JSON or YAML-ish)",
    )
    p.add_argument(
        "--log",
        "-l",
        dest="logs",
        action="append",
        type=Path,
        required=True,
        help="Tool-call JSONL path (repeatable)",
    )
    p.add_argument(
        "--format",
        "-f",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    p.add_argument(
        "--fail-on-orphan",
        action="store_true",
        help="Exit 2 if any declared tool was never called",
    )
    p.add_argument(
        "--fail-on-rogue",
        action="store_true",
        help="Exit 3 if any called tool was not in the manifest",
    )
    p.add_argument(
        "--max-orphan-ratio",
        type=float,
        default=None,
        metavar="R",
        help="Exit 4 if orphan_ratio exceeds R (e.g. 0.25)",
    )
    p.add_argument(
        "--min-coverage",
        type=float,
        default=None,
        metavar="C",
        help="Exit 5 if declared-tool coverage is below C (e.g. 0.8)",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.manifest.is_file():
        print(f"error: manifest not found: {args.manifest}", file=sys.stderr)
        return 1
    missing = [p for p in args.logs if not p.is_file()]
    if missing:
        print(f"error: log not found: {missing[0]}", file=sys.stderr)
        return 1

    try:
        declared = load_manifest(args.manifest)
        called = load_call_counts(args.logs)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not declared:
        print("error: no tool names found in manifest", file=sys.stderr)
        return 1

    result = diff_tools(declared, called)
    sys.stdout.write(_format_json(result) if args.format == "json" else _format_text(result))

    if args.fail_on_orphan and result.orphans:
        return 2
    if args.fail_on_rogue and result.rogues:
        return 3
    if args.max_orphan_ratio is not None and result.orphan_ratio > args.max_orphan_ratio:
        return 4
    if args.min_coverage is not None and result.coverage < args.min_coverage:
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
