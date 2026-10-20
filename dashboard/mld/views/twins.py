from __future__ import annotations
import streamlit as st

from .. import charts, ui


def render(ld, manifest, show_votes: bool):
    if not show_votes:
        return ui.votes_locked()
    tw, pairs = ld.table("twins"), ld.table("twin_pairs")
    if tw.empty:
        return ui.no_votes()
    with st.expander("How taste twins are calculated"):
        st.markdown(
            "For each pair of voters, only songs **both** could vote on are compared (not their own songs, not rounds either skipped).\n\n"
            "- **Cosine similarity** (70%): did they put their points on the same songs in similar amounts? 1 = identical pattern.\n"
            "- **Jaccard similarity** (30%): of the songs either scored, what share did both score?\n"
            "- **Combined** = 0.7 x cosine + 0.3 x Jaccard. A voter's twin is the other voter with the highest combined score.\n"
            "- A pair needs at least 4 shared voted rounds. **Near tie** means the runner-up is within 0.03, so treat the twin as one of two or three.")
    show = tw.copy()
    for col in ("near_tie", "confidence", "margin_to_runner_up", "runner_up", "shared_rounds", "shared_songs", "top_shared_songs"):
        if col not in show:
            show[col] = None
    show["match"] = show["near_tie"].map({True: "Near tie", False: ""})
    if show["twin"].isna().all():
        st.info("No voter has enough shared voting with another to name a taste twin yet (needs 4+ shared rounds).")
    cols = ["voter", "twin", "twin_combined", "confidence", "match", "margin_to_runner_up", "runner_up", "shared_rounds", "shared_songs", "top_shared_songs"]
    st.dataframe(show[[c for c in cols if c in show]].rename(columns={
        "voter": "Voter", "twin": "Taste twin", "twin_combined": "Combined", "confidence": "Confidence", "match": "Note",
        "margin_to_runner_up": "Lead over runner-up", "runner_up": "Runner-up", "shared_rounds": "Shared rounds",
        "shared_songs": "Shared songs", "top_shared_songs": "Top shared songs"}), hide_index=True, width="stretch",
        column_config={"Combined": st.column_config.NumberColumn(format="%.2f"), "Lead over runner-up": st.column_config.NumberColumn(format="%.3f"), "Top shared songs": st.column_config.TextColumn(width="large")})

    st.markdown("**Similarity between every pair**")
    order = sorted(set(pairs["voter"]))
    hm = charts.heatmap(pairs, "other", "voter", "combined", tooltip=["voter", "other", "combined", "cosine", "jaccard", "shared_rounds", "shared_songs", "status"],
                        x_sort=order, y_sort=order, label_format=".2f", title="Combined", height=max(320, 24 * len(order) + 90))
    st.altair_chart(hm, width="stretch")
    ui.note("Gray cells have too little shared voting to compare.")

    st.markdown("**Drill down**")
    v = st.selectbox("Voter", order, key="tw_voter")
    d = pairs[(pairs["voter"] == v)].dropna(subset=["combined"]).sort_values("combined", ascending=False)
    if d.empty:
        st.info("Not enough shared voting to compare this voter.")
        return
    st.altair_chart(charts.bar_h(d, "other", "combined", tooltip=["other", "combined", "cosine", "jaccard", "shared_rounds", "shared_songs"],
                                 x_title=f"Combined similarity with {v}"), width="stretch")
    row = tw[tw["voter"] == v].iloc[0]
    if isinstance(row.get("top_shared_songs"), str) and row["top_shared_songs"]:
        st.markdown(f"Songs {v} and {row['twin']} both scored: {row['top_shared_songs']}")
