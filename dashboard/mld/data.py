"""Load the analysis output folder. Everything is cached on the manifest's run timestamp."""
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass
import pandas as pd
import streamlit as st

DEFAULT_OUT = os.environ.get("ML_OUT", "out")


class OutputMissing(Exception):
    pass


def manifest_file(out_dir: str) -> str:
    return os.path.join(out_dir, "manifest.json")


@st.cache_data(show_spinner=False)
def _manifest(out_dir: str, mtime: float) -> dict:
    with open(manifest_file(out_dir), encoding="utf-8") as fh:
        return json.load(fh)


def load_manifest(out_dir: str) -> dict:
    p = manifest_file(out_dir)
    if not os.path.exists(p):
        raise OutputMissing(f"No manifest.json in '{out_dir}'. Run the analysis script first: "
                            "python -m ml_analysis --workbook <tracker.xlsx> --out " + out_dir)
    return _manifest(out_dir, os.path.getmtime(p))


@st.cache_data(show_spinner=False)
def _read(path: str, run_utc: str) -> pd.DataFrame:
    return pd.read_csv(path)


@dataclass
class LeagueData:
    out_dir: str
    league: int
    run_utc: str
    summary: dict

    def table(self, name: str) -> pd.DataFrame:
        p = os.path.join(self.out_dir, f"league_{self.league}", f"{name}.csv")
        if not os.path.exists(p):
            return pd.DataFrame()
        try:
            return _read(p, self.run_utc)
        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    def base(self, name: str) -> pd.DataFrame:
        p = os.path.join(self.out_dir, "data", f"{name}.csv")
        if not os.path.exists(p):
            return pd.DataFrame()
        df = _read(p, self.run_utc)
        return df[df["league"] == self.league].copy() if "league" in df.columns else df

    @property
    def has_votes(self) -> bool:
        return not self.table("fans").empty

    def narratives(self) -> dict:
        p = os.path.join(self.out_dir, f"league_{self.league}", "profile_narratives.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        return {}


def load_league(out_dir: str, manifest: dict, league: int) -> LeagueData:
    p = os.path.join(out_dir, f"league_{league}", "summary.json")
    with open(p, encoding="utf-8") as fh:
        summary = json.load(fh)
    return LeagueData(out_dir, league, manifest["run_utc"], summary)


def league_title(label: str) -> str:
    return re.sub(r"\s*\(\d+(?:st|nd|rd|th) League\)\s*$", "", str(label))


def league_options(manifest: dict) -> dict:
    """{display label: league number} for every analyzed league."""
    out = {}
    for s in manifest.get("leagues", []):
        out[f"League {s['league']}: {league_title(s['league_label'])}"] = int(s["league"])
    return out
