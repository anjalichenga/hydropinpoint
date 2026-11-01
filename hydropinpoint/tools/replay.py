"""Adapter for Person A's historical replay implementation."""
from __future__ import annotations

import contextlib
import importlib
import io
from datetime import UTC, datetime
from typing import Any

from hydropinpoint.contracts import ToolResult


def replay(**kwargs: Any) -> ToolResult:
    try:
        module = importlib.import_module("hydropinpoint.replay.run")
        if hasattr(module, "run"):
            value = module.run(**kwargs)
        else:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                module.main()
            value = {"report": output.getvalue()}
        if isinstance(value, ToolResult):
            return value
        return ToolResult(
            value=value,
            source="HydroPinpoint historical replay",
            fetched_at=datetime.now(UTC),
        )
    except Exception as exc:
        return ToolResult(
            value=None,
            source="HydroPinpoint historical replay",
            fetched_at=datetime.now(UTC),
            error=f"Historical replay is unavailable: {exc}",
        )
