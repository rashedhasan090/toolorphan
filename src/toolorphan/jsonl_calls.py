"""Extract tool call names and counts from agent tool-call JSONL."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

# Events that mention a tool name but are not invocations
_SKIP_EVENTS = {
    "tool_result",
    "result",
    "observation",
    "tool_response",
    "function_response",
}


def _name_from_record(obj: dict[str, Any]) -> str | None:
    for key in ("tool", "name", "tool_name", "function_name"):
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    fn = obj.get("function")
    if isinstance(fn, dict):
        val = fn.get("name")
        if isinstance(val, str) and val.strip():
            return val.strip()

    tc = obj.get("tool_call")
    if isinstance(tc, dict):
        nested = _name_from_record(tc)
        if nested:
            return nested

    return None


def _names_from_record(obj: dict[str, Any]) -> list[str]:
    """Return all tool names present on one JSONL record."""
    names: list[str] = []

    tcs = obj.get("tool_calls")
    if isinstance(tcs, list) and tcs:
        for item in tcs:
            if isinstance(item, dict):
                n = _name_from_record(item)
                if n:
                    names.append(n)
        if names:
            return names

    single = _name_from_record(obj)
    if single:
        names.append(single)
    return names


def _should_skip(obj: dict[str, Any]) -> bool:
    for key in ("type", "event", "role", "kind"):
        val = obj.get(key)
        if isinstance(val, str) and val.lower() in _SKIP_EVENTS:
            return True
    return False


def load_call_counts(paths: list[Path]) -> Counter[str]:
    """Count tool invocations across one or more JSONL files."""
    counts: Counter[str] = Counter()
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON — {exc}") from exc
                if not isinstance(obj, dict):
                    continue
                if _should_skip(obj):
                    continue
                for name in _names_from_record(obj):
                    counts[name] += 1
    return counts
