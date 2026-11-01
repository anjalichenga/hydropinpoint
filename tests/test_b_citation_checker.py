from datetime import UTC, datetime

from hydropinpoint.agent.citation_checker import check_numbers
from hydropinpoint.contracts import ToolResult


def test_citation_checker_removes_unsupported_number() -> None:
    result = ToolResult(value={"diameter_m": 0.4}, source="test", fetched_at=datetime.now(UTC))
    answer, table = check_numbers("Required diameter is 0.4 m. Capacity ratio is 2.", [result])
    assert "0.4" in answer
    assert "ratio" not in answer
    assert table[0]["source"] == "test"
