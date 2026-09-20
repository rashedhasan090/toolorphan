"""Parse agent tool manifests into a set of declared tool names."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


_NAME_KEYS = ("name", "tool", "id", "tool_name", "function_name")


def _as_name(value: Any) -> str | None:
    if isinstance(value, str):
        name = value.strip()
        return name or None
    return None


def _name_from_mapping(obj: dict[str, Any]) -> str | None:
    for key in _NAME_KEYS:
        name = _as_name(obj.get(key))
        if name:
            return name
    fn = obj.get("function")
    if isinstance(fn, dict):
        name = _as_name(fn.get("name"))
        if name:
            return name
    return None


def _collect_from_list(items: Iterable[Any], out: set[str]) -> None:
    for item in items:
        if isinstance(item, str):
            name = _as_name(item)
            if name:
                out.add(name)
        elif isinstance(item, dict):
            name = _name_from_mapping(item)
            if name:
                out.add(name)


def _collect_from_obj(obj: Any, out: set[str]) -> None:
    if isinstance(obj, list):
        _collect_from_list(obj, out)
        return
    if not isinstance(obj, dict):
        return

    # Direct tools / functions arrays (OpenAI, Anthropic-ish, MCP exports)
    for key in ("tools", "functions", "tool_list", "available_tools", "declarations"):
        if key in obj:
            _collect_from_obj(obj[key], out)

    # Dict keyed by tool name: {"Shell": {...}, "Read": {...}}
    tools = obj.get("tools")
    if isinstance(tools, dict):
        for key, value in tools.items():
            name = _as_name(key)
            if name:
                out.add(name)
            if isinstance(value, dict):
                nested = _name_from_mapping(value)
                if nested:
                    out.add(nested)

    # Single tool object
    name = _name_from_mapping(obj)
    if name and "tools" not in obj and "functions" not in obj:
        out.add(name)


_YAML_NAME_LINE = re.compile(
    r"""^\s*(?:-\s*)?(?:name|tool|id|tool_name)\s*:\s*["']?([^"'#\n]+)["']?\s*(?:#.*)?$""",
    re.IGNORECASE,
)
_YAML_BARE_LIST = re.compile(r"""^\s*-\s+["']?([A-Za-z_][\w./:-]*)["']?\s*(?:#.*)?$""")


def _parse_yaml_lite(text: str) -> set[str]:
    """Tiny YAML subset extractor — no PyYAML dependency."""
    names: set[str] = set()
    for line in text.splitlines():
        m = _YAML_NAME_LINE.match(line)
        if m:
            name = m.group(1).strip()
            if name and name.lower() not in {"true", "false", "null", "~"}:
                names.add(name)
            continue
        m = _YAML_BARE_LIST.match(line)
        if m:
            names.add(m.group(1).strip())
    return names


def load_manifest(path: Path) -> set[str]:
    """Load declared tool names from JSON or YAML-ish manifest."""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    names: set[str] = set()

    if suffix in {".json", ".jsonc"}:
        # Strip simple // comments for .jsonc friendliness
        cleaned = re.sub(r"^\s*//.*?$", "", text, flags=re.MULTILINE)
        data = json.loads(cleaned)
        _collect_from_obj(data, names)
        return names

    if suffix in {".yaml", ".yml"}:
        # Prefer JSON-in-YAML if the whole file is JSON
        stripped = text.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                data = json.loads(text)
                _collect_from_obj(data, names)
                if names:
                    return names
            except json.JSONDecodeError:
                pass
        return _parse_yaml_lite(text)

    # Extension-less / .txt: try JSON first, then YAML-lite
    try:
        data = json.loads(text)
        _collect_from_obj(data, names)
        if names:
            return names
    except json.JSONDecodeError:
        pass
    return _parse_yaml_lite(text)
