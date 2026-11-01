from datetime import UTC, datetime

from hydropinpoint.agent.citation_checker import check_numbers
from hydropinpoint.contracts import ToolResult


def test_citation_checker_removes_unsupported_number() -> None:
    result = ToolResult(value={"diameter_m": 0.4}, source="test", fetched_at=datetime.now(UTC))
    answer, table = check_numbers("Required diameter is 0.4 m. Capacity ratio is 2.", [result])
    assert "0.4" in answer
    assert "ratio" not in answer
    assert table[0]["source"] == "test"


def test_citation_checker_accepts_rounded_value() -> None:
    result = ToolResult(
        value={"runoff_coeff_C": 0.3459558},
        source="terrain model",
        fetched_at=datetime.now(UTC),
    )
    answer, table = check_numbers("The runoff coefficient is 0.35.", [result])
    assert answer == "The runoff coefficient is 0.35."
    assert table[0]["source"] == "terrain model"


def test_citation_checker_maps_timestamp_year() -> None:
    result = ToolResult(
        value={},
        source="forecast service",
        fetched_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    answer, table = check_numbers("The data was fetched in 2026.", [result])
    assert answer == "The data was fetched in 2026."
    assert table[0]["source"] == "forecast service"
