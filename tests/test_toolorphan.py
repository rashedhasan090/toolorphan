"""Tests for toolorphan."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toolorphan.diff import diff_tools
from toolorphan.jsonl_calls import load_call_counts
from toolorphan.manifest import load_manifest
from toolorphan.cli import main

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def test_load_json_manifest():
    names = load_manifest(EXAMPLES / "manifest.json")
    assert names == {"Shell", "Read", "WebSearch", "SendEmail", "LegacyDB"}


def test_load_yaml_manifest():
    names = load_manifest(EXAMPLES / "manifest.yaml")
    assert "Shell" in names and "LegacyDB" in names


def test_load_keyed_manifest(tmp_path: Path):
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"tools": {"Alpha": {}, "Beta": {"name": "Beta"}}}), encoding="utf-8")
    assert load_manifest(path) == {"Alpha", "Beta"}


def test_call_counts():
    counts = load_call_counts([EXAMPLES / "run.jsonl"])
    assert counts["Shell"] == 2
    assert counts["Read"] == 2
    assert counts["WebSearch"] == 1
    assert counts["UndeclaredHack"] == 1
    assert counts["GhostMCP"] == 1


def test_diff():
    declared = load_manifest(EXAMPLES / "manifest.json")
    called = load_call_counts([EXAMPLES / "run.jsonl"])
    result = diff_tools(declared, called)
    assert set(result.orphans) == {"SendEmail", "LegacyDB"}
    assert set(result.rogues) == {"UndeclaredHack", "GhostMCP"}
    matched_names = {n for n, _ in result.matched}
    assert matched_names == {"Shell", "Read", "WebSearch"}
    assert result.coverage == pytest.approx(0.6)


def test_cli_text_and_gates(capsys):
    code = main(
        [
            "--manifest",
            str(EXAMPLES / "manifest.json"),
            "--log",
            str(EXAMPLES / "run.jsonl"),
            "--fail-on-orphan",
            "--fail-on-rogue",
        ]
    )
    out = capsys.readouterr().out
    assert "Orphans" in out
    assert "Rogues" in out
    assert code == 2  # orphan gate fires first


def test_cli_json(capsys):
    code = main(
        [
            "--manifest",
            str(EXAMPLES / "manifest.json"),
            "--log",
            str(EXAMPLES / "run.jsonl"),
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert "orphans" in payload and "rogues" in payload
    assert code == 0


def test_cli_min_coverage(capsys):
    code = main(
        [
            "--manifest",
            str(EXAMPLES / "manifest.json"),
            "--log",
            str(EXAMPLES / "run.jsonl"),
            "--min-coverage",
            "0.9",
        ]
    )
    assert code == 5
