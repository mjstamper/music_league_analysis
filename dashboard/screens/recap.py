"""Recap ("Wrapped") page: story cards for the whole group, for all complete leagues, one league, or a named period."""
import os
import pandas as pd
import streamlit as st

from mld import context, recap_data, recap_ui

ctx = context.setup()
st.markdown(recap_ui.CSS, unsafe_allow_html=True)
scopes = recap_data.scope_options(ctx.manifest)
if not scopes:
    st.info("No recap found in the output folder. Re-run the analysis (mode all or recap) to create it.")
    st.stop()

with st.sidebar:
    label = st.selectbox("Recap for", list(scopes), key="recap_scope")
scope_key = scopes[label]
rd = recap_data.load_scope(ctx.out_dir, ctx.manifest, scope_key)

rounds_path = os.path.join(ctx.out_dir, "data", "rounds.csv")
rounds_n = int(pd.read_csv(rounds_path)["league"].isin(rd.scope["leagues"]).sum()) if os.path.exists(rounds_path) else 0
slides, skipped = recap_ui.build_slides(rd, ctx.show_votes, rounds_n)

head, mode_col = st.columns([4, 2])
head.title("Music League Wrapped")
mode = mode_col.radio("View", ["Story", "All awards"], horizontal=True, key="recap_mode", label_visibility="collapsed")

if skipped:
    with st.expander(f"Awards not shown ({len(skipped)})"):
        for name, why in skipped:
            st.markdown(f"- **{name}**: {why}")

if mode == "Story":
    sk = f"{scope_key}|{ctx.show_votes}"
    if st.session_state.get("story_key") != sk:
        st.session_state["story_key"], st.session_state["story_i"] = sk, 0
    n = len(slides)
    i = min(max(st.session_state.get("story_i", 0), 0), n - 1)

    def go(delta):
        st.session_state["story_i"] = min(max(st.session_state["story_i"] + delta, 0), n - 1)

    def jump(key):
        st.session_state["story_i"] = labels.index(st.session_state[key])

    labels = [f"{k + 1}. {s.kicker if k else 'Start'}" for k, s in enumerate(slides)]
    b1, b2, mid, jmp = st.columns([1, 1, 4, 3])
    b1.button("Back", on_click=go, args=(-1,), disabled=i == 0, width="stretch")
    b2.button("Next", on_click=go, args=(1,), disabled=i == n - 1, type="primary", width="stretch")
    mid.progress((i + 1) / n, text=f"Slide {i + 1} of {n}")
    jkey = f"jump_{sk}_{i}"
    jmp.selectbox("Jump to", labels, index=i, key=jkey, on_change=jump, args=(jkey,), label_visibility="collapsed")
    recap_ui.render_slide(slides[i])
else:
    recap_ui.render_slide(slides[0], show_notes=False)
    body = slides[1:]
    for k in range(0, len(body), 2):
        cols = st.columns(2)
        for c, s in zip(cols, body[k:k + 2]):
            with c:
                recap_ui.render_slide(s)
