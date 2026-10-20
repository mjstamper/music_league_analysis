"""Load the tracker workbook (v2.1 structure), validate it, and derive per-song / per-round facts.

Everything downstream works on the `Dataset` object. No metric logic lives here.
"""
from __future__ import annotations
import hashlib
import os
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from .config import Config
from .util import competition_places

SONG_COLS = {
    "Song": "song", "Artist": "artist", "Genre": "genre", "Submitter": "submitter", "Round": "round_label",
    "Points": "points", "# of Voters": "n_voters", "League": "league_label", "League #": "league",
    "Round #": "round", "Spotify URI": "uri",
}
SONG_OPTIONAL = {"Subgenre": "subgenre", "Major Genre": "major_genre", "Place #": "wb_place",
                 "Raw Points": "wb_raw_points", "Status": "wb_status"}
VOTE_COLS = {"League #": "league", "Round #": "round", "Voter": "voter", "Spotify URI": "uri", "Points": "points"}
ROUND_COLS = {"League #": "league", "Round #": "round", "Round Name": "round_name", "Description": "description",
              "Point Budget": "budget", "Songs per Person": "songs_per_person", "Max Votes per Song": "cap_input"}


class DataError(Exception):
    """The workbook is not in the expected shape; the message says what to fix."""


@dataclass
class Dataset:
    songs: pd.DataFrame
    votes: pd.DataFrame          # clean: positive, non-self, de-duplicated, joined to a song
    ballots: pd.DataFrame        # one row per (league, round, voter)
    rounds: pd.DataFrame         # one row per (league, round)
    participants: list
    validation: pd.DataFrame     # check, value, expected, status, detail
    meta: dict = field(default_factory=dict)

    def leagues(self) -> list:
        return sorted(int(x) for x in self.songs["league"].unique())


def _read(path, sheet, required, optional=None):
    try:
        df = pd.read_excel(path, sheet_name=sheet)
    except ValueError as e:
        raise DataError(f"Sheet '{sheet}' not found in {os.path.basename(path)}. This script expects the v2.1 "
                        f"tracker structure (tabs: All Song Rankings, Votes, Rounds, Participants).") from e
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataError(f"Sheet '{sheet}' is missing required columns: {missing}")
    keep = list(required) + [c for c in (optional or []) if c in df.columns]
    return df[keep].copy()


def _clean_text(s: pd.Series) -> pd.Series:
    s = s.astype("object").where(s.notna(), None)
    return s.map(lambda x: " ".join(str(x).split()) if x is not None else None)


def load_dataset(path: str, cfg: Config | None = None) -> Dataset:
    cfg = cfg or Config()
    checks = []

    def add(check, value, expected=None, kind="expect", detail=""):
        if kind == "info":
            status = "INFO"
        else:
            status = "PASS" if value == expected else "FAIL"
        checks.append(dict(check=check, value=value, expected=expected, status=status, detail=detail))

    # ---------- read ----------
    raw_s = _read(path, "All Song Rankings", list(SONG_COLS), list(SONG_OPTIONAL))
    raw_v = _read(path, "Votes", list(VOTE_COLS))
    raw_r = _read(path, "Rounds", ["League #", "Round #", "Round Name"], list(ROUND_COLS)[3:])
    raw_p = _read(path, "Participants", ["Name"])

    songs = raw_s.rename(columns={**SONG_COLS, **SONG_OPTIONAL})
    for c in SONG_OPTIONAL.values():
        if c not in songs.columns:
            songs[c] = np.nan
    for c in ["song", "artist", "genre", "submitter", "round_label", "league_label", "uri", "subgenre", "major_genre"]:
        songs[c] = _clean_text(songs[c])
    songs["league"] = songs["league"].astype(int)
    songs["round"] = songs["round"].astype(int)
    songs["points"] = pd.to_numeric(songs["points"], errors="coerce")
    songs["n_voters"] = pd.to_numeric(songs["n_voters"], errors="coerce")
    songs["round_name"] = songs["round_label"].map(lambda x: x.split(" - ", 1)[1] if x and " - " in x else x)
    songs = songs.reset_index(drop=True)
    songs["song_idx"] = songs.index

    votes = raw_v.rename(columns=VOTE_COLS)
    votes["voter"] = _clean_text(votes["voter"])
    votes["uri"] = _clean_text(votes["uri"])
    votes["league"] = votes["league"].astype(int)
    votes["round"] = votes["round"].astype(int)
    votes["points"] = pd.to_numeric(votes["points"], errors="coerce")

    rounds_in = raw_r.rename(columns=ROUND_COLS)
    for c in ROUND_COLS.values():
        if c not in rounds_in.columns:
            rounds_in[c] = np.nan
    rounds_in["league"] = rounds_in["league"].astype(int)
    rounds_in["round"] = rounds_in["round"].astype(int)
    participants = sorted(_clean_text(raw_p["Name"]).dropna().unique())

    # ---------- row-level validation ----------
    add("Song rows", len(songs), kind="info")
    add("Vote rows read", len(votes), kind="info")
    dup_key = songs[songs["uri"].notna()].duplicated(["league", "round", "uri"], keep=False)
    add("Duplicate (league, round, URI) in songs", int(dup_key.sum()), 0)
    bad_pts = votes["points"].isna() | (votes["points"] <= 0)
    add("Vote rows with missing or non-positive points (dropped)", int(bad_pts.sum()), 0)
    votes = votes[~bad_pts].copy()
    votes["points"] = votes["points"].astype(int)
    blank = votes["voter"].isna() | votes["uri"].isna()
    add("Vote rows with blank voter or URI (dropped)", int(blank.sum()), 0)
    votes = votes[~blank].copy()
    dups = votes.duplicated(["league", "round", "voter", "uri"], keep="first")
    add("Duplicate vote rows (dropped)", int(dups.sum()), 0)
    votes = votes[~dups].copy()

    keyed = songs[songs["uri"].notna()][["league", "round", "uri", "song_idx", "submitter"]]
    votes = votes.merge(keyed, on=["league", "round", "uri"], how="left", validate="many_to_one")
    unjoined = votes["song_idx"].isna()
    add("Vote rows that do not join to a song", int(unjoined.sum()), 0,
        detail="Join key is (League #, Round #, Spotify URI)")
    if unjoined.any() and cfg.halt_on_unjoined:
        sample = votes[unjoined].head(5)[["league", "round", "voter", "uri"]].to_dict("records")
        raise DataError(f"{int(unjoined.sum())} vote rows do not join to a song, e.g. {sample}. "
                        "Fix the Votes or All Song Rankings tab, or set halt_on_unjoined=false.")
    votes = votes[~unjoined].copy()
    votes["song_idx"] = votes["song_idx"].astype(int)
    selfv = votes["voter"] == votes["submitter"]
    add("Self-votes (dropped)", int(selfv.sum()), 0)
    votes = votes[~selfv].copy().reset_index(drop=True)
    add("Valid vote rows used", len(votes), kind="info")
    add("Valid vote points used", int(votes["points"].sum()), kind="info")

    names = set(participants)
    add("Submitters not on Participants", int((~songs["submitter"].dropna().isin(names)).sum()), 0)
    add("Voters not on Participants", int((~votes["voter"].isin(names)).sum()), 0)

    # ---------- ballots ----------
    ballots = (votes.groupby(["league", "round", "voter"])
               .agg(n_votes=("points", "size"), points=("points", "sum")).reset_index())
    ballot_sets = {k: set(g["voter"]) for k, g in ballots.groupby(["league", "round"])}

    # ---------- per-song facts ----------
    agg = votes.groupby("song_idx").agg(raw_points=("points", "sum"), raw_voters=("points", "size"))
    songs = songs.merge(agg, left_on="song_idx", right_index=True, how="left")
    songs["raw_points"] = songs["raw_points"].fillna(0).astype(int)
    songs["raw_voters"] = songs["raw_voters"].fillna(0).astype(int)
    songs["elig"] = [len(ballot_sets.get((l, r), set()) - ({s} if s else set()))
                     for l, r, s in zip(songs["league"], songs["round"], songs["submitter"])]
    songs["submitter_voted"] = [(s in ballot_sets.get((l, r), set())) if s else None
                                for l, r, s in zip(songs["league"], songs["round"], songs["submitter"])]

    # official place: recomputed within (league, round) from typed Points and # of Voters
    songs["place"] = np.nan
    for _, idx in songs[songs["points"].notna()].groupby(["league", "round"]).groups.items():
        sub = songs.loc[idx]
        songs.loc[idx, "place"] = competition_places(sub["points"], sub["n_voters"].fillna(0))
    songs["round_size"] = songs.groupby(["league", "round"])["song_idx"].transform("size")
    songs["round_pct"] = np.where(songs["round_size"] > 1, (songs["place"] - 1) / (songs["round_size"] - 1), np.nan)

    # status (same definitions as the workbook's Status column)
    def status(r):
        if pd.isna(r.points):
            return "Unscored"
        if r.points == 0 and r.raw_points == 0:
            return "Zero-vote"
        if r.points == r.raw_points and r.n_voters == r.raw_voters:
            return "OK"
        if r.points == 0 and r.raw_points > 0 and r.submitter_voted is False:
            return "Forfeited"
        return "Mismatch"
    songs["status"] = songs.apply(status, axis=1)

    # ---------- rounds ----------
    r = songs.groupby(["league", "round"]).agg(
        round_name=("round_name", "first"), league_label=("league_label", "first"), songs=("song_idx", "size"),
        scored=("points", lambda s: bool(s.notna().any())),
        forfeited=("status", lambda s: int((s == "Forfeited").sum())),
        submitters=("submitter", lambda s: int(s.notna().sum())),
    ).reset_index()
    r = r.merge(rounds_in.drop(columns=["round_name"]), on=["league", "round"], how="left")
    r["ballots"] = [len(ballot_sets.get((l, rr), set())) for l, rr in zip(r["league"], r["round"])]
    r["cap_input"] = pd.to_numeric(r["cap_input"], errors="coerce")
    r["cap"] = [cfg.cap_overrides.get(l, c if pd.notna(c) else cfg.default_cap) for l, c in zip(r["league"], r["cap_input"])]
    r["cap_known"] = [(l in cfg.cap_overrides) or pd.notna(c) for l, c in zip(r["league"], r["cap_input"])]
    r["songs_per_person"] = pd.to_numeric(r["songs_per_person"], errors="coerce")
    r["budget"] = pd.to_numeric(r["budget"], errors="coerce")
    league_rounds = r.groupby("league").agg(n_rounds=("round", "size"), n_scored=("scored", "sum"))
    league_rounds["complete"] = (league_rounds["n_scored"] == league_rounds["n_rounds"]) & \
                                (league_rounds["n_rounds"] >= cfg.min_league_rounds)
    r["league_complete"] = r["league"].map(league_rounds["complete"])
    missing_rounds = set(zip(songs["league"], songs["round"])) - set(zip(rounds_in["league"], rounds_in["round"]))
    add("Song rounds missing from Rounds tab", len(missing_rounds), 0)

    songs = songs.merge(r[["league", "round", "cap", "cap_known", "budget"]], on=["league", "round"], how="left")
    songs["norm"] = np.where((songs["points"].notna()) & (songs["elig"] > 0),
                             songs["points"] / (songs["elig"] * songs["cap"]), np.nan)

    # ---------- reconcile with the workbook's own formula columns ----------
    if songs["wb_place"].notna().any():
        sc = songs[songs["points"].notna()]
        add("Place: script vs workbook Place # differences", int((sc["place"] != sc["wb_place"]).sum()), 0)
    if songs["wb_raw_points"].notna().any():
        has = songs["uri"].notna()
        add("Raw Points: script vs workbook differences", int((songs.loc[has, "raw_points"] != pd.to_numeric(songs.loc[has, "wb_raw_points"])).sum()), 0)
    if songs["wb_status"].notna().any():
        add("Status: script vs workbook differences", int((songs["status"] != songs["wb_status"]).sum()), 0)
    for st in ["OK", "Forfeited", "Zero-vote", "Unscored"]:
        add(f"Songs with status {st}", int((songs["status"] == st).sum()), kind="info")
    add("Songs with status Mismatch", int((songs["status"] == "Mismatch").sum()), 0)

    with open(path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    meta = dict(workbook=os.path.basename(path), sha256=sha, modified=pd.Timestamp(os.path.getmtime(path), unit="s").isoformat(),
                subgenre_filled=int(songs["subgenre"].notna().sum()), songs=len(songs),
                cap_known_rounds=int(r["cap_known"].sum()), rounds=len(r))
    return Dataset(songs=songs, votes=votes, ballots=ballots, rounds=r, participants=participants,
                   validation=pd.DataFrame(checks), meta=meta)
