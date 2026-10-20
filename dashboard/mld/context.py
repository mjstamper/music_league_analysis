"""Shared sidebar and settings for every page."""
from __future__ import annotations
import os
from dataclasses import dataclass
import streamlit as st

from . import data


@dataclass
class Ctx:
    out_dir: str
    manifest: dict
    show_votes: bool


def setup() -> Ctx:
    with st.sidebar:
        out_dir = st.text_input("Analysis output folder", value=data.DEFAULT_OUT, key="out_dir", help="Folder written by: python -m ml_analysis")
        if st.button("Reload data"):
            st.cache_data.clear()
        try:
            manifest = data.load_manifest(out_dir)
        except data.OutputMissing as e:
            st.error(str(e))
            st.stop()
        show_votes = st.checkbox("Show who voted for whom", value=os.environ.get("ML_SHOW_VOTES", "1") == "1", key="show_votes",
                                 help="Turn off before sharing: hides fan and twin views and the voting-based parts of profiles and the recap.")
        st.caption(f"Data as of {manifest['run_utc'].replace('T', ' ')[:16]} UTC")
    return Ctx(out_dir, manifest, show_votes)
