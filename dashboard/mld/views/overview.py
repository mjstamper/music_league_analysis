from __future__ import annotations
import altair as alt
import pandas as pd
import streamlit as st

from .. import charts, ui


def render(ld, manifest):
    songs, lb, rr, rounds = ld.table("songs"), ld.table("leaderboard"), ld.table("round_results"), ld.base("rounds")
    s = ld.summary
    ballots = ld.base("ballots")
    people = set(songs["submitter"].dropna()) | (set(ballots["voter"]) if len(ballots) else set())
    forf = int((songs["status"] == "Forfeited").sum()) if len(songs) else 0
    zero = int((songs["status"] == "Zero-vote").sum()) if len(songs) else 0
    ui.kpis([("Rounds scored", f"{s['scored_rounds']} of {s['rounds']}"), ("Songs", f"{len(songs):,}"), ("People", len(people)),
             ("Vote points", f"{s['vote_points']:,}"), ("Forfeited songs", forf, "Submitter did not vote that round, so the song's official points are zero."),
             ("Zero-vote songs", zero, "Songs that received no votes.")])

    st.subheader("Standings")
    if lb.empty:
        st.info("No rounds have been scored yet. Submissions are listed under Round explorer.")
    else:
        long = pd.concat([
            lb.assign(series="Official points", value=lb["official_points"]),
            lb.assign(series="Lost to forfeits", value=lb["points_lost_to_forfeits"].clip(lower=0)),
        ])[["submitter", "series", "value", "rank", "wins", "podiums"]]
        order = lb.sort_values("official_points", ascending=False)["submitter"].tolist()
        chart = alt.Chart(long.replace({float("nan"): None})).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("submitter:N", sort=order, title=None),
            x=alt.X("value:Q", title="Points", stack="zero"),
            color=alt.Color("series:N", scale=alt.Scale(domain=["Official points", "Lost to forfeits"], range=[charts.ACCENT, "#C9D3CF"]),
                            legend=alt.Legend(title=None, orient="bottom")),
            order=alt.Order("series:N", sort="descending"),
            tooltip=["submitter", "series", "value", "rank", "wins", "podiums"]).properties(height=max(200, 28 * len(lb) + 40))
        c1, c2 = st.columns([11, 9])
        c1.altair_chart(chart, width="stretch")
        c2.dataframe(lb[["rank", "submitter", "official_points", "avg_points_per_submission", "wins", "podiums", "forfeited_songs"]]
                     .rename(columns={"submitter": "Player", "official_points": "Points", "avg_points_per_submission": "Avg / submission",
                                      "wins": "Wins", "podiums": "Podiums", "forfeited_songs": "Forfeits", "rank": "#"}),
                     hide_index=True, width="stretch",
                     column_config={"Avg / submission": st.column_config.NumberColumn(format="%.2f")})
        ui.note("Official points follow the Music League results: a song whose submitter skipped voting counts as zero. "
                "The lighter bar shows the raw votes lost this way.")

    st.subheader("Round winners")
    if rr.empty:
        st.caption("No scored rounds yet.")
    else:
        w = rr[rr["place"] == 1].groupby(["round", "round_name"]).agg(
            Song=("song", " & ".join), Artist=("artist", " & ".join), Submitter=("submitter", " & ".join),
            Points=("points", "max"), Tied=("song", lambda x: "Tie" if len(x) > 1 else "")).reset_index()
        st.dataframe(w.rename(columns={"round": "Round", "round_name": "Name"}), hide_index=True, width="stretch")

    st.subheader("Round explorer")
    if rounds.empty:
        return
    labels = {f"Round {int(r.round)}: {r.round_name}": int(r.round) for r in rounds.sort_values("round").itertuples()}
    pick = st.selectbox("Round", list(labels), index=len(labels) - 1 if songs["points"].isna().all() else 0, key="ov_round")
    rd = songs[songs["round"] == labels[pick]].copy()
    if rd["points"].isna().all():
        st.info("This round has not been scored yet. Submitter and points appear after the reveal.")
        st.dataframe(rd[["song", "artist", "genre"]].rename(columns={"song": "Song", "artist": "Artist", "genre": "Genre"}),
                     hide_index=True, width="stretch")
        return
    rd["label"] = rd["song"] + " (" + rd["submitter"].fillna("?") + ")"
    chart = charts.bar_h(rd, "label", "points", color="status",
                         color_scale=alt.Scale(domain=charts.STATUS_DOMAIN, range=charts.STATUS_RANGE),
                         tooltip=["song", "artist", "submitter", "points", "raw_points", "raw_voters", "elig", "place", "status"],
                         x_title="Official points", text="points")
    st.altair_chart(chart, width="stretch")
    ui.note("Gray = forfeited (submitter skipped voting). Amber = no votes recorded.")
