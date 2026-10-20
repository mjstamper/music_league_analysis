from __future__ import annotations
import streamlit as st

from .. import charts, ui

DIMS = {"major_genre": "Major genre", "genre": "Genre label (as entered)", "subgenre": "Subgenre"}


def render(ld, manifest):
    gs = ld.table("genre_summary")
    if gs.empty:
        st.info("No genre data for this league.")
        return
    avail = [d for d in DIMS if d in set(gs["dimension"])]
    dim = st.radio("Group by", avail, format_func=DIMS.get, horizontal=True, key="gn_dim")
    if "subgenre" not in avail:
        ui.note("Subgenres are not available yet: the workbook's Subgenre column is empty. They appear here once genre research is stored there.")
    d = gs[gs["dimension"] == dim].copy()
    d["Top 5"] = d["top_n"].map({True: "Top 5", False: "Other"})
    c1, c2 = st.columns(2)
    c1.markdown("**Songs submitted**")
    c1.altair_chart(charts.bar_h(d, "label", "songs", color="Top 5", color_scale=charts.alt.Scale(domain=["Top 5", "Other"], range=[charts.ACCENT, "#C9D3CF"]),
                                 tooltip=["label", "songs", "share_of_songs", "distinct_submitters", "total_official_points"], x_title="Songs", text="songs"),
                    width="stretch")
    c2.markdown("**Average points per scored song**")
    dd = d.dropna(subset=["avg_points_per_scored_song"])
    c2.altair_chart(charts.bar_h(dd, "label", "avg_points_per_scored_song", tooltip=["label", "avg_points_per_scored_song", "songs"],
                                 x_title="Average official points", sort="-x"), width="stretch")
    ui.note("Averages use songs with normal results only (not forfeited or zero-vote). Small genres vary a lot: check the song counts.")
    st.dataframe(d[["popularity_rank", "label", "songs", "share_of_songs", "distinct_submitters", "total_official_points", "avg_points_per_scored_song"]].rename(columns={
        "popularity_rank": "#", "label": "Genre", "songs": "Songs", "share_of_songs": "Share", "distinct_submitters": "Submitters",
        "total_official_points": "Total points", "avg_points_per_scored_song": "Avg points / song"}), hide_index=True, width="stretch",
        column_config={"Share": st.column_config.NumberColumn(format="percent"), "Avg points / song": st.column_config.NumberColumn(format="%.2f")})
