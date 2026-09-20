"""Diff declared tools vs observed calls."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class DiffResult:
    declared: set[str]
    called: Counter[str]
    orphans: list[str] = field(default_factory=list)  # declared, never called
    rogues: list[str] = field(default_factory=list)  # called, never declared
    matched: list[tuple[str, int]] = field(default_factory=list)  # (name, count)

    @property
    def orphan_ratio(self) -> float:
        if not self.declared:
            return 0.0
        return len(self.orphans) / len(self.declared)

    @property
    def coverage(self) -> float:
        """Fraction of declared tools that were called at least once."""
        if not self.declared:
            return 1.0
        return len(self.matched) / len(self.declared)


def diff_tools(declared: set[str], called: Counter[str]) -> DiffResult:
    called_names = set(called.keys())
    orphans = sorted(declared - called_names)
    rogues = sorted(called_names - declared)
    matched = sorted(
        ((name, called[name]) for name in (declared & called_names)),
        key=lambda x: (-x[1], x[0]),
    )
    return DiffResult(
        declared=set(declared),
        called=Counter(called),
        orphans=orphans,
        rogues=rogues,
        matched=matched,
    )
