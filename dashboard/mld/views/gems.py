from __future__ import annotations
import altair as alt
import numpy as np
import streamlit as st

from .. import charts, ui


def render(ld, manifest):
    top, ranked, excl = ld.table("gems"), ld.table("gems_ranked"), ld.table("gems_excluded_forfeit")
    if ranked.empty:
        return ui.no_votes() if not ld.has_votes else st.info("No songs meet the underrated-gem criteria in this league.")
    g = ld.summary.get("gems", {})
    with st.expander("What counts as an underrated gem?"):
        st.markdown(
            "Songs that finished in the **bottom half of their round** but were liked by **many different voters**. Breadth matters more than depth.\n\n"
            "- Eligible pool: at least 3 eligible voters, at least 2 who gave points, finish in the bottom half, not forfeited.\n"
            "- **Gem score** = 0.7 x breadth percentile (share of eligible voters who gave points) + 0.3 x bad-finish percentile.\n"
            "- Ties are broken by average points from those who voted for it.")
    ui.kpis([("Songs in the pool", g.get("pool_size", len(ranked))),
             ("Same top 5 at 50/50 weights?", "Yes" if g.get("same_members_at_alt_weights") else "No",
              "Re-scoring with equal weight on breadth and finish. 'No' means the list depends on the 70/30 choice.")], 2)
    t = top.assign(breadth_pct=ui.pct(top["breadth"]), voters=top["raw_voters"].astype(str) + " of " + top["elig"].astype(str),
                   finish=top["place"].map(ui.ordinal) + (" of " + top["round_size"].astype(int).astype(str) if "round_size" in top else ""),
                   also=top["in_top_at_alt_weights"].map({True: "Yes", False: "No"}))
    st.markdown("**Top underrated gems**")
    st.dataframe(t[["song", "artist", "submitter", "round_name", "finish", "voters", "breadth_pct", "gem_score", "also"]].rename(columns={
        "song": "Song", "artist": "Artist", "submitter": "Submitter", "round_name": "Round", "finish": "Finish", "voters": "Voters who gave points",
        "breadth_pct": "Breadth", "gem_score": "Gem score", "also": "Also top 5 at 50/50"}), hide_index=True, width="stretch",
        column_config={"Breadth": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100), "Artist": st.column_config.TextColumn(width="medium"), "Song": st.column_config.TextColumn(width="medium"), "Gem score": st.column_config.NumberColumn(format="%.2f")})

    st.markdown("**Where the gems sit**")
    d = ranked.assign(group=np.where(ranked["rank"] <= len(top), "Top gems", "Other candidates"))
    base = alt.Chart(d.replace({np.nan: None})).mark_circle(opacity=0.8, stroke="white").encode(
        x=alt.X("round_pct:Q", title="Finish in round (left = better, right = worse)", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0.45, 1.02])),
        y=alt.Y("breadth:Q", title="Share of eligible voters who gave points", axis=alt.Axis(format="%")),
        size=alt.Size("avg_points_positive_voters:Q", legend=None, scale=alt.Scale(range=[50, 400])),
        color=alt.Color("group:N", scale=alt.Scale(domain=["Top gems", "Other candidates"], range=[charts.ACCENT, "#C9D3CF"]), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=["song", "artist", "submitter", "round_name", "place", "raw_voters", "elig", "breadth", "gem_score"])
    labels = alt.Chart(d[d["group"] == "Top gems"].replace({np.nan: None})).mark_text(align="left", dx=8, dy=-7, fontSize=10).encode(
        x="round_pct:Q", y="breadth:Q", text="song:N")
    st.altair_chart((base + labels).properties(height=380), width="stretch")
    ui.note("Top gems sit toward the upper right: a poor finish despite wide support.")
    if len(excl):
        with st.expander(f"Excluded: {len(excl)} forfeited songs that would otherwise qualify"):
            st.dataframe(excl[["song", "artist", "submitter", "round_name", "raw_voters", "elig"]].rename(columns={
                "song": "Song", "artist": "Artist", "submitter": "Submitter", "round_name": "Round", "raw_voters": "Voters", "elig": "Eligible"}),
                hide_index=True, width="stretch")
            ui.note("Their official points were zeroed because the submitter skipped voting, so a low finish says nothing about the song.")
