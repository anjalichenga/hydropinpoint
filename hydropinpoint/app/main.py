"""Four-page Streamlit interface for HydroPinpoint."""
from __future__ import annotations

import folium
import streamlit as st
from streamlit_folium import st_folium

from hydropinpoint.agent.graph import ask
from hydropinpoint.config import DEFAULT_BOX, UI_MAP_TILES, UI_PAGE_TITLE
from hydropinpoint.pipeline import run_cached
from hydropinpoint.tools.replay import replay


@st.cache_resource(ttl=900, show_spinner=False)
def _engine_result():
    return run_cached(DEFAULT_BOX)


def _load():
    try:
        with st.spinner("Loading live terrain, rainfall and drainage data..."):
            return _engine_result()
    except Exception as exc:
        st.error(f"Live screening is unavailable: {exc}")
        return None


def _citation_rows(citations: list[dict]) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for citation in citations:
        value = str(citation.get("number", ""))
        source = citation.get("source")
        if not value or not source:
            continue
        key = (value, str(source))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"Value": value, "Verified source": str(source)})
    return rows


def _live_page() -> None:
    st.header("Live screening")
    st.caption("Screening only — not a flood prediction or surcharge model.")
    result = _load()
    if result is None:
        return
    critical_notes = [note for note in result.notes if "OSM drainage lookup" not in note]
    if critical_notes:
        st.warning("Degraded mode: " + "; ".join(critical_notes))
    peak_rain = max(
        (value for cell in result.rainfall.cells for value in cell.mm_per_h),
        default=0.0,
    )
    if peak_rain == 0:
        st.info("The current forecast is dry; required runoff-driven sizes are zero.")
    centre = [(result.box.south + result.box.north) / 2, (result.box.west + result.box.east) / 2]
    map_view = folium.Map(location=centre, zoom_start=12, tiles=UI_MAP_TILES)
    map_view.fit_bounds(
        [[result.box.south, result.box.west], [result.box.north, result.box.east]]
    )
    sizing = {row.hotspot_id: row for row in result.sizings}
    for hotspot in result.hotspots:
        drain = sizing[hotspot.id]
        required = max(drain.hourly_required_D_m, default=0.0)
        mapped = drain.mapped_drain_size_m
        popup = (
            f"Hotspot {hotspot.id}<br>Rank {hotspot.susceptibility_rank}<br>"
            f"Peak Q: {max(hotspot.hourly_Q_m3s, default=0):.3f} m³/s<br>"
            f"Required diameter: {required:.3f} m<br>"
            f"Mapped size: {mapped if mapped is not None else 'capacity unknown'}"
        )
        folium.CircleMarker(
            [hotspot.lat, hotspot.lon], radius=6, popup=popup,
            color="#b91c1c" if hotspot.susceptibility_rank <= 3 else "#2563eb",
            fill=True,
        ).add_to(map_view)
    st_folium(map_view, use_container_width=True, height=560)
    top = sorted(result.hotspots, key=lambda row: row.susceptibility_rank)[:3]
    st.dataframe([
        {
            "rank": row.susceptibility_rank,
            "hotspot": row.id,
            "peak Q (m³/s)": max(row.hourly_Q_m3s, default=0.0),
            "required D (m)": max(sizing[row.id].hourly_required_D_m, default=0.0),
            "mapped size (m)": sizing[row.id].mapped_drain_size_m,
            "capacity": sizing[row.id].capacity_note,
        }
        for row in top
    ], use_container_width=True)


def _ask_page() -> None:
    st.header("Ask HydroPinpoint")
    st.caption("General questions are instant; live hotspot questions reuse a 15-minute cache.")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    for message in st.session_state.chat_messages:
        st.chat_message(message["role"]).write(message["content"])
    question = st.chat_input("Ask about hotspots, wards, facilities, routes, or a mm/h scenario")
    if question:
        st.session_state.chat_messages.append({"role": "user", "content": question})
        st.chat_message("user").write(question)
        with st.status("Answering...", expanded=False):
            state = ask(question)
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": state["answer"]}
        )
        st.chat_message("assistant").write(state["answer"])
        citation_rows = _citation_rows(state.get("citations", []))
        if citation_rows:
            with st.expander("Verified numeric sources"):
                st.dataframe(
                    citation_rows,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Value": st.column_config.TextColumn("Value", width="small"),
                        "Verified source": st.column_config.TextColumn(
                            "Verified source", width="large"
                        ),
                    },
                )


def _replay_page() -> None:
    st.header("HISTORICAL REPLAY")
    st.warning("Historical replay results must never be mixed with live or scenario values.")
    if st.button("Run 5 September 2022 replay"):
        with st.spinner("Running historical replay..."):
            result = replay()
        if result.error:
            st.error(result.error)
        elif isinstance(result.value, dict) and "report" in result.value:
            st.code(result.value["report"])
        else:
            st.json(result.value)


def _sources_page() -> None:
    st.header("Sources")
    result = _load()
    if result is None:
        return
    st.write({
        "rainfall": result.rainfall.source,
        "rainfall fetched_at": result.rainfall.fetched_at.isoformat(),
        "DEM vintage": result.dem_vintage,
        "landcover vintage": result.landcover_vintage,
        "generated_at": result.generated_at.isoformat(),
        "notes": result.notes,
    })


def main() -> None:
    st.set_page_config(page_title=UI_PAGE_TITLE, layout="wide")
    st.title("HydroPinpoint")
    page = st.sidebar.radio("Page", ("Live", "Ask", "Replay", "Sources"))
    {"Live": _live_page, "Ask": _ask_page, "Replay": _replay_page, "Sources": _sources_page}[page]()


if __name__ == "__main__":
    main()
