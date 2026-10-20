"""Small UI helpers shared by every view."""
from __future__ import annotations
import pandas as pd
import streamlit as st

CSS = """
<style>
div[data-testid="stMetric"] {background:#F3F7F5; border-radius:10px; padding:10px 14px;}
div[data-testid="stMetricLabel"] p {font-size:0.8rem; color:#5B6F68;}
h1 {letter-spacing:-0.5px;}
.small-note {color:#5B6F68; font-size:0.85rem;}
</style>
"""


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def kpis(items, cols=None):
    cols = st.columns(cols or len(items))
    for c, (label, value, *rest) in zip(cols, items):
        c.metric(label, value, help=rest[0] if rest else None)


def note(text: str):
    st.markdown(f"<span class='small-note'>{text}</span>", unsafe_allow_html=True)


def votes_locked():
    st.info("Voting relationships are hidden. Turn on 'Show who voted for whom' in the sidebar to see this view.")


def no_votes():
    st.info("This league has no votes yet, so vote-based views are unavailable. Standings and submissions appear once rounds are scored.")


def pct(series: pd.Series) -> pd.Series:
    return series * 100


def ordinal(n) -> str:
    if pd.isna(n):
        return ""
    n = int(n)
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
