"""Ward-boundary tool."""
from hydropinpoint.contracts import ToolResult
from hydropinpoint.fetch.wards import fetch_wards


def wards() -> ToolResult:
    return fetch_wards()

