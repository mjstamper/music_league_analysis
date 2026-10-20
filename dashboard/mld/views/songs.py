from __future__ import annotations
import altair as alt
import streamlit as st

from .. import charts, ui

COLS = {"round_name": "Round", "song": "Song", "artist": "Artist", "submitter": "Submitter", "major_genre": "Genre", "place": "Place",
        "points": "Points", "raw_voters": "Voters", "elig": "Eligible", "avg_points_eligible": "Avg / eligible voter",
        "share_pct": "Voters %", "status": "Status"}


def render(ld, manifest):
    st_ = ld.table("songs")
    if st_.empty:
        st.info("No songs for this league.")
        return
    st_ = st_.copy()
    st_["share_pct"] = ui.pct(st_["share_eligible_voting"])
    with st.expander("Filters", expanded=False):
        c = st.columns(4)
        rs = c[0].multiselect("Round", sorted(st_["round_name"].unique(), key=lambda x: int(st_[st_["round_name"] == x]["round"].iloc[0])), key="sg_r")
        sb = c[1].multiselect("Submitter", sorted(st_["submitter"].dropna().unique()), key="sg_s")
        gn = c[2].multiselect("Genre", sorted(st_["major_genre"].dropna().unique()), key="sg_g")
        sts = c[3].multiselect("Status", sorted(st_["status"].unique()), key="sg_st")
        q = st.text_input("Search song or artist", key="sg_q")
    d = st_
    if rs: d = d[d["round_name"].isin(rs)]
    if sb: d = d[d["submitter"].isin(sb)]
    if gn: d = d[d["major_genre"].isin(gn)]
    if sts: d = d[d["status"].isin(sts)]
    if q: d = d[d["song"].str.contains(q, case=False, na=False) | d["artist"].str.contains(q, case=False, na=False)]

    t1, t2 = ld.table("top_songs_total_points"), ld.table("top_songs_avg_per_eligible_voter")
    if len(t1):
        show = lambda df: df[["song", "artist", "submitter", "raw_points", "raw_voters", "avg_points_eligible", "status"]].rename(
            columns={"song": "Song", "artist": "Artist", "submitter": "Submitter", "raw_points": "Votes pts", "raw_voters": "Voters",
                     "avg_points_eligible": "Avg / eligible", "status": "Status"})
        cc = {"Avg / eligible": st.column_config.NumberColumn(format="%.2f"), "Artist": st.column_config.TextColumn(width="medium")}
        st.markdown("**Top 5 by total points**")
        st.dataframe(show(t1), hide_index=True, width="stretch", column_config=cc)
        st.markdown("**Top 5 by average points per eligible voter**")
        st.dataframe(show(t2), hide_index=True, width="stretch", column_config=cc)
        ui.note("Rankings use raw vote points. A forfeited song can appear here because its votes were real, even though its official points were zeroed.")

    st.markdown(f"**All songs** ({len(d)} shown)")
    st.dataframe(d.sort_values(["round", "place"])[list(COLS)].rename(columns=COLS), hide_index=True, width="stretch", height=420,
                 column_config={"Avg / eligible voter": st.column_config.NumberColumn(format="%.2f"), "Artist": st.column_config.TextColumn(width="medium"),
                                "Song": st.column_config.TextColumn(width="medium"),
                                "Voters %": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)})

    sc = d[d["points"].notna() & d["raw_voters"].gt(0)]
    if len(sc):
        st.markdown("**Broad appeal vs strong appeal**")
        sc = sc.assign(label=sc["song"] + " (" + sc["submitter"].fillna("?") + ")")
        ch = charts.scatter(sc, "share_eligible_voting", "avg_points_positive_voters", size="raw_points", color="major_genre",
                            tooltip=["song", "artist", "submitter", "round_name", "raw_points", "raw_voters", "elig", "place"],
                            x_title="Share of eligible voters who gave points", y_title="Average points from those who voted for it")
        st.altair_chart(ch.encode(x=alt.X("share_eligible_voting:Q", title="Share of eligible voters who gave points", axis=alt.Axis(format="%"))), width="stretch")
        ui.note("Right = more people voted for it. Up = those who did gave more points. Bubble size = total points.")
