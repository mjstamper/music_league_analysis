"""Write results to disk in a layout a dashboard can read, plus manifest.json describing the run."""
from __future__ import annotations
import json
import os
import platform
from datetime import datetime, timezone
import pandas as pd

from . import __version__
from .config import Config
from .data import Dataset


def _csv(df: pd.DataFrame, path: str, files: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    files.append(dict(path=path, rows=int(len(df))))


def _json(obj, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))


def write_all(ds: Dataset, cfg: Config, out: str, league_results: dict, recaps: dict) -> dict:
    files: list = []
    rel = lambda p: os.path.relpath(p, out).replace(os.sep, "/")
    d = os.path.join(out, "data")
    songs = ds.songs.drop(columns=["wb_place", "wb_raw_points", "wb_status"], errors="ignore")
    _csv(songs, os.path.join(d, "songs.csv"), files)
    _csv(ds.votes[["league", "round", "voter", "uri", "points", "song_idx", "submitter"]].rename(columns={"submitter": "song_submitter"}),
         os.path.join(d, "votes.csv"), files)
    _csv(ds.ballots, os.path.join(d, "ballots.csv"), files)
    _csv(ds.rounds, os.path.join(d, "rounds.csv"), files)
    _csv(pd.DataFrame({"name": ds.participants}), os.path.join(d, "participants.csv"), files)
    _csv(ds.validation, os.path.join(d, "validation.csv"), files)

    league_index = []
    for n, res in sorted(league_results.items()):
        ld = os.path.join(out, f"league_{n}")
        for name, df in res.items():
            if name.startswith("_") or not isinstance(df, pd.DataFrame):
                continue
            _csv(df, os.path.join(ld, f"{name}.csv"), files)
        _json(res["_summary"], os.path.join(ld, "summary.json"))
        league_index.append(res["_summary"])

    scopes_meta = []
    for key, rc in recaps.items():
        rd = os.path.join(out, "recap", key)
        recap = rc["result"]
        awards_meta = []
        for a in recap["awards"]:
            entry = a.to_dict()
            entry["files"] = []
            if a.table is not None:
                p = os.path.join(rd, f"award_{a.key}.csv"); _csv(a.table, p, files); entry["files"].append(rel(p))
            for nm, df in a.extra_tables.items():
                p = os.path.join(rd, f"award_{a.key}__{nm}.csv"); _csv(df, p, files); entry["files"].append(rel(p))
            if a.ineligible is not None:
                p = os.path.join(rd, f"award_{a.key}__ineligible.csv"); _csv(a.ineligible, p, files); entry["files"].append(rel(p))
            awards_meta.append(entry)
        _json(dict(key=key, label=rc["label"], leagues=rc["leagues"], scope=recap["scope"], awards=awards_meta), os.path.join(rd, "awards.json"))
        scopes_meta.append(dict(key=key, label=rc["label"], leagues=rc["leagues"], folder=rel(rd), scope=recap["scope"],
                                awards=[{k: x[k] for k in ("key", "title", "status", "winners", "headline")} for x in awards_meta]))
    if scopes_meta:
        _json(dict(scopes=[{k: x[k] for k in ("key", "label", "leagues", "folder")} for x in scopes_meta]), os.path.join(out, "recap", "index.json"))

    v = ds.validation
    warnings = []
    if not ds.rounds["cap_known"].all():
        warnings.append(f"Max Votes per Song is blank for {int((~ds.rounds['cap_known']).sum())} of {len(ds.rounds)} rounds: normalized scores and "
                        "share-of-available-points are 'points per eligible voter' (approximate). Fill in the Rounds tab or set cap_overrides.")
    if ds.meta["subgenre_filled"] == 0:
        warnings.append("Subgenre column is empty: subgenre results are unavailable until genre research is stored in the workbook.")
    inprog = sorted(ds.rounds[~ds.rounds["league_complete"].fillna(False)]["league"].unique())
    if inprog:
        warnings.append(f"Leagues not complete (excluded from the recap): {[int(x) for x in inprog]}.")
    warnings.append("Recap performance measures exclude statuses: " + ", ".join(cfg.performance_excluded_statuses) +
                    ". Set performance_excluded_statuses in the config to change this (e.g. keep Zero-vote songs).")
    manifest = dict(
        schema_version=2, script_version=__version__, run_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python=platform.python_version(), pandas=pd.__version__, workbook=ds.meta,
        config=cfg.to_dict(), leagues_available=ds.leagues(),
        leagues_complete=sorted(int(x) for x in ds.rounds[ds.rounds["league_complete"].fillna(False)]["league"].unique()),
        leagues_analyzed=sorted(league_results),
        validation=dict(pass_=int((v["status"] == "PASS").sum()), fail=int((v["status"] == "FAIL").sum()),
                        failures=v[v["status"] == "FAIL"][["check", "value", "expected"]].to_dict("records")),
        warnings=warnings, leagues=league_index, recap_scopes=scopes_meta,
        files=[dict(path=rel(f["path"]), rows=f["rows"]) for f in files])
    _json(manifest, os.path.join(out, "manifest.json"))
    return manifest
