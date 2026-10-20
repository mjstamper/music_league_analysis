"""League view page."""
import streamlit as st

from mld import context, data
from mld.views import checks, fans, genres, gems, overview, profiles, songs, twins

ctx = context.setup()
opts = data.league_options(ctx.manifest)
if not opts:
    st.error("The output folder has no league results.")
    st.stop()
with st.sidebar:
    scored = [i for i, s_ in enumerate(ctx.manifest["leagues"]) if s_["scored_rounds"] > 0]
    label = st.selectbox("League", list(opts), index=scored[-1] if scored else 0, key="league_pick")

league = opts[label]
ld = data.load_league(ctx.out_dir, ctx.manifest, league)
s = ld.summary
manifest, show_votes = ctx.manifest, ctx.show_votes

st.title(label)
st.caption(f"{s['scored_rounds']} of {s['rounds']} rounds scored · {s['songs']} songs · {s['vote_rows']:,} votes · mode: {s['mode']}")

notes = list(manifest["warnings"])
if manifest["validation"]["fail"]:
    st.error(f"{manifest['validation']['fail']} validation check(s) failed. See the Data checks tab.")
if s["mode"] != "full":
    st.info("This league has no votes yet. Standings, songs and genres are shown; fans, twins, gems and profiles need votes.")
with st.expander(f"Data notes ({len(notes)})"):
    for n in notes:
        st.markdown(f"- {n}")

tabs = st.tabs(["Overview", "Songs", "Fans", "Taste twins", "Underrated gems", "Genres", "Profiles", "Data checks"])
with tabs[0]: overview.render(ld, manifest)
with tabs[1]: songs.render(ld, manifest)
with tabs[2]: fans.render(ld, manifest, show_votes)
with tabs[3]: twins.render(ld, manifest, show_votes)
with tabs[4]: gems.render(ld, manifest)
with tabs[5]: genres.render(ld, manifest)
with tabs[6]: profiles.render(ld, manifest, show_votes)
with tabs[7]: checks.render(ld, manifest, ctx.out_dir)
