from __future__ import annotations
import os
import pandas as pd
import streamlit as st

from .. import ui


def render(ld, manifest, out_dir):
    v = pd.read_csv(os.path.join(out_dir, "data", "validation.csv")) if os.path.exists(os.path.join(out_dir, "data", "validation.csv")) else pd.DataFrame()
    mv = manifest["validation"]
    ui.kpis([("Checks passed", mv["pass_"]), ("Checks failed", mv["fail"]), ("Run (UTC)", manifest["run_utc"].replace("T", " ")[:16]),
             ("Workbook", manifest["workbook"]["workbook"])])
    if mv["fail"]:
        st.error("Some validation checks failed. Treat results with care until they are fixed.")
        st.dataframe(pd.DataFrame(mv["failures"]), hide_index=True, width="stretch")
    st.markdown("**Data validation (whole workbook)**")
    if len(v):
        st.dataframe(v, hide_index=True, width="stretch")
    qc = ld.table("qc")
    if len(qc):
        st.markdown(f"**League {ld.league} reconciliation**")
        st.dataframe(qc, hide_index=True, width="stretch")
    st.markdown("**Settings used for this run**")
    st.json(manifest["config"], expanded=False)
    st.markdown("**Download tables**")
    folder = os.path.join(out_dir, f"league_{ld.league}")
    files = sorted(f for f in os.listdir(folder) if f.endswith(".csv"))
    pick = st.selectbox("Table", files, key="dl_pick")
    with open(os.path.join(folder, pick), "rb") as fh:
        st.download_button("Download CSV", fh.read(), file_name=f"league_{ld.league}_{pick}", mime="text/csv")
