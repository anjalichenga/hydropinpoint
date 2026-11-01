"""Plain-code numeric citation guardrail."""
from __future__ import annotations

import math
import re
from typing import Any

from hydropinpoint.contracts import ToolResult

NUMBER = re.compile(r"(?<![\w.-])-?\d+(?:\.\d+)?")


def _numbers(value: Any) -> list[float]:
    found: list[float] = []
    if isinstance(value, bool) or value is None:
        return found
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, dict):
        for child in value.values():
            found.extend(_numbers(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            found.extend(_numbers(child))
    return found


def check_numbers(answer: str, results: list[ToolResult]) -> tuple[str, list[dict[str, Any]]]:
    sources: list[tuple[float, str]] = []
    for result in results:
        sources.extend((number, result.source) for number in _numbers(result.value))
    table: list[dict[str, Any]] = []
    unsupported: set[str] = set()
    for token in NUMBER.findall(answer):
        number = float(token)
        matches = [
            source
            for candidate, source in sources
            if math.isclose(number, candidate, rel_tol=1e-6, abs_tol=1e-9)
        ]
        table.append({"number": token, "source": matches[0] if matches else None})
        if not matches:
            unsupported.add(token)
    if unsupported:
        safe_sentences = [
            sentence for sentence in re.split(r"(?<=[.!?])\s+", answer)
            if not any(token in NUMBER.findall(sentence) for token in unsupported)
        ]
        answer = " ".join(safe_sentences).strip()
        if not answer:
            answer = "The available sources do not support a numeric answer."
    return answer, table

