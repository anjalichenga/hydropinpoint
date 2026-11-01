from hydropinpoint.app.main import _citation_rows


def test_citation_rows_are_readable_and_deduplicated() -> None:
    citations = [
        {"number": "0.35", "source": "Terrain model"},
        {"number": "0.35", "source": "Terrain model"},
        {"number": "2", "source": None},
        {"number": "1.2", "source": "Drain sizing"},
    ]

    assert _citation_rows(citations) == [
        {"Value": "0.35", "Verified source": "Terrain model"},
        {"Value": "1.2", "Verified source": "Drain sizing"},
    ]
