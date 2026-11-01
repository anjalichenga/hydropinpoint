"""Adapter for Person A's historical replay implementation."""
from __future__ import annotations

import importlib
from datetime import UTC, datetime
from typing import Any

from hydropinpoint.contracts import ToolResult


def replay(**kwargs: Any) -> ToolResult:
    try:
        module = importlib.import_module("hydropinpoint.replay.run")
        function = getattr(module, "run")
        value = function(**kwargs)
        if isinstance(value, ToolResult):
            return value
        return ToolResult(
            value=value,
            source="HydroPinpoint historical replay",
            fetched_at=datetime.now(UTC),
        )
    except (ModuleNotFoundError, AttributeError) as exc:
        return ToolResult(
            value=None,
            source="HydroPinpoint historical replay",
            fetched_at=datetime.now(UTC),
            error=f"Person A replay is unavailable: {exc}",
        )

