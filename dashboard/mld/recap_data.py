"""Load one recap scope (a folder under out/recap/) written by ml_analysis."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
import pandas as pd
import streamlit as st

from .data import _read


def scope_options(manifest: dict) -> dict:
    """{label: scope key} in the order the script wrote them (all complete leagues first)."""
    return {s["label"]: s["key"] for s in manifest.get("recap_scopes", [])}


@dataclass
class RecapData:
    out_dir: str
    run_utc: str
    meta: dict            # contents of awards.json

    @property
    def awards(self) -> dict:
        return {a["key"]: a for a in self.meta["awards"]}

    @property
    def scope(self) -> dict:
        return self.meta["scope"]

    def has(self, key: str) -> bool:
        a = self.awards.get(key)
        return bool(a) and a["status"] != "no eligible players"

    def table(self, key: str, extra: str | None = None) -> pd.DataFrame:
        name = f"award_{key}__{extra}.csv" if extra else f"award_{key}.csv"
        for f in self.awards.get(key, {}).get("files", []):
            if f.endswith("/" + name):
                p = os.path.join(self.out_dir, f)
                try:
                    return _read(p, self.run_utc)
                except (pd.errors.EmptyDataError, FileNotFoundError):
                    return pd.DataFrame()
        return pd.DataFrame()

    def notes(self, key: str) -> list:
        return self.awards.get(key, {}).get("notes", [])


@st.cache_data(show_spinner=False)
def _awards(path: str, run_utc: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_scope(out_dir: str, manifest: dict, key: str) -> RecapData:
    folder = next(s["folder"] for s in manifest["recap_scopes"] if s["key"] == key)
    return RecapData(out_dir, manifest["run_utc"], _awards(os.path.join(out_dir, folder, "awards.json"), manifest["run_utc"]))
