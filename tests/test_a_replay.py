from hydropinpoint.contracts import Hotspot
from hydropinpoint.replay.run import rank_for_event, select_replay_hotspots


def _hotspot(
    hotspot_id: int,
    peak_q: float,
    susceptibility: float,
) -> Hotspot:
    return Hotspot(
        id=hotspot_id,
        lat=12.95,
        lon=77.65,
        catchment_area_km2=0.1,
        depression_depth_m=1.0,
        imperviousness=0.8,
        runoff_coeff_C=0.8,
        flow_path_slope_S=0.005,
        susceptibility_score=susceptibility,
        susceptibility_rank=hotspot_id,
        hourly_Q_m3s=[peak_q],
    )


def test_replay_ranks_peak_event_runoff_before_static_score() -> None:
    static_first = _hotspot(1, peak_q=0.2, susceptibility=0.95)
    event_first = _hotspot(2, peak_q=0.8, susceptibility=0.50)

    ranked = rank_for_event([static_first, event_first])

    assert [hotspot.id for hotspot in ranked] == [2, 1]


def test_replay_uses_static_score_to_break_runoff_tie() -> None:
    lower_static = _hotspot(1, peak_q=0.8, susceptibility=0.50)
    higher_static = _hotspot(2, peak_q=0.8, susceptibility=0.90)

    ranked = rank_for_event([lower_static, higher_static])

    assert [hotspot.id for hotspot in ranked] == [2, 1]


def test_replay_keeps_best_static_candidate_with_event_leaders() -> None:
    hotspots = [
        _hotspot(index, peak_q=float(20 - index), susceptibility=0.5)
        for index in range(1, 12)
    ]
    static_best = hotspots[-1]
    static_best.susceptibility_rank = 1
    static_best.susceptibility_score = 0.99
    for index, hotspot in enumerate(hotspots[:-1], start=2):
        hotspot.susceptibility_rank = index

    selected = select_replay_hotspots(hotspots)

    assert len(selected) == 11
    assert static_best in selected
