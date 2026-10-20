from __future__ import annotations
import altair as alt
import streamlit as st

from .. import charts, ui


def render(ld, manifest, show_votes: bool):
    if not show_votes:
        return ui.votes_locked()
    fans, pairs = ld.table("fans"), ld.table("fan_pairs")
    if fans.empty:
        return ui.no_votes()
    st.markdown("**Biggest fan of each submitter**")
    show = fans.assign(share=ui.pct(fans["share_of_received"]))[
        ["submitter", "biggest_fan", "tie", "fan_points", "songs_scored_by_fan", "avg_points_per_scored_song", "share", "total_received", "forfeited_songs"]]
    st.dataframe(show.rename(columns={"submitter": "Submitter", "biggest_fan": "Biggest fan", "tie": "Tie", "fan_points": "Fan's points",
                                      "songs_scored_by_fan": "Songs scored", "avg_points_per_scored_song": "Avg / scored song",
                                      "share": "Share of all received", "total_received": "Total received", "forfeited_songs": "Forfeited songs"}),
                 hide_index=True, width="stretch",
                 column_config={"Avg / scored song": st.column_config.NumberColumn(format="%.2f"),
                                "Share of all received": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)})
    ui.note("Biggest fan = the voter who gave a submitter the most points across the league (raw votes, so forfeited songs still count). "
            "Ties list every tied voter.")

    st.markdown("**Who gave points to whom**")
    order = sorted(set(pairs["voter"]) | set(pairs["submitter"]))
    hm = charts.heatmap(pairs, "submitter", "voter", "points", tooltip=["voter", "submitter", "points", "songs_scored"],
                        x_sort=order, y_sort=order, title="Points", height=max(300, 24 * len(order) + 90))
    st.altair_chart(hm, width="stretch")
    ui.note("Rows are voters, columns are submitters. Empty cells mean no points were given.")

    st.markdown("**Drill down**")
    sub = st.selectbox("Submitter", sorted(fans["submitter"]), key="fan_sub")
    d = pairs[pairs["submitter"] == sub].sort_values("points", ascending=False)
    st.altair_chart(charts.bar_h(d, "voter", "points", tooltip=["voter", "points", "songs_scored"], x_title=f"Points given to {sub}", text="points"),
                    width="stretch")
