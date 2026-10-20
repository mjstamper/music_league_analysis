from __future__ import annotations
import streamlit as st

from .. import charts, ui


def render(ld, manifest, show_votes: bool):
    ps = ld.table("profile_summary")
    subs = ld.table("profile_submissions")
    if ps.empty:
        return ui.no_votes()
    person = st.selectbox("Person", sorted(ps["person"]), key="pf_person")
    r = ps[ps["person"] == person].iloc[0]
    kp = [("Submissions", int(r["submissions"])), ("Ballots cast", int(r["ballots"]))]
    if show_votes:
        kp += [("Points given", int(r["points_given"])), ("Biggest fan", r["biggest_fan"] if isinstance(r["biggest_fan"], str) else "-"),
               ("Taste twin", r["taste_twin"] if isinstance(r["taste_twin"], str) else "-"),
               ("Most supported", r["most_supported_submitter"] if isinstance(r["most_supported_submitter"], str) else "-")]
    ui.kpis(kp)
    if isinstance(r["missing_rounds"], str) and r["missing_rounds"]:
        st.warning(f"No submission recorded for round(s): {r['missing_rounds']}.")

    nar = ld.narratives().get(person)
    if nar:
        st.markdown(f"> {nar}")
    else:
        ui.note("Written profile not generated yet. Add league_N/profile_narratives.json to show one here.")

    st.markdown("**Submissions**")
    mine = subs[subs["submitter"] == person].sort_values("round")
    st.dataframe(mine[["round", "round_name", "song", "artist", "major_genre", "subgenre", "place", "points", "status"]].rename(columns={
        "round": "Rd", "round_name": "Round", "song": "Song", "artist": "Artist", "major_genre": "Genre", "subgenre": "Subgenre",
        "place": "Place", "points": "Points", "status": "Status"}).dropna(axis=1, how="all"), hide_index=True, width="stretch")

    mix = ld.table("profile_mix")
    mm = mix[(mix["person"] == person) & (mix["dimension"] == "major_genre")]
    if len(mm) and show_votes:
        st.markdown("**Genres: what they submit vs what they reward**")
        long = mm.melt(id_vars=["label"], value_vars=["submitted_share", "rewarded_share"], var_name="series", value_name="share")
        long["series"] = long["series"].map({"submitted_share": "Submitted", "rewarded_share": "Rewarded with points"})
        st.altair_chart(charts.grouped_bar(long, "label", "share", "series"), width="stretch")
        ui.note("Submitted = share of their songs. Rewarded = share of the points they gave.")
    elif len(mm):
        sub_only = mm[["label", "submitted_share"]].rename(columns={"submitted_share": "share"})
        st.markdown("**Genres they submit**")
        st.altair_chart(charts.bar_h(sub_only, "label", "share", x_title="Share of their songs"), width="stretch")

    if not show_votes:
        return
    tv, sup = ld.table("profile_top_votes"), ld.table("profile_support")
    c1, c2 = st.columns(2)
    c1.markdown("**Songs they rewarded most**")
    t = tv[tv["person"] == person]
    c1.dataframe(t[["song", "artist", "submitter", "points_given"]].rename(columns={"song": "Song", "artist": "Artist", "submitter": "Submitter", "points_given": "Points"}),
                 hide_index=True, width="stretch")
    c2.markdown("**Most supported**")
    dim = c2.radio("By", ["submitter", "artist", "major_genre"], horizontal=True, key="pf_dim",
                   format_func=lambda x: {"submitter": "Submitter", "artist": "Artist", "major_genre": "Genre"}[x])
    s = sup[(sup["person"] == person) & (sup["dimension"] == dim)].head(8)
    c2.dataframe(s.assign(share=ui.pct(s["share"]))[["label", "points_given", "share"]].rename(columns={"label": dim.replace("_", " ").title(), "points_given": "Points", "share": "Share"}),
                 hide_index=True, width="stretch", column_config={"Share": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100)})
