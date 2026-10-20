"""Per-league analysis: standings, song leaders, fans, taste twins, underrated gems, genres, profile data."""
from __future__ import annotations
import numpy as np
import pandas as pd

from .config import Config
from .data import Dataset
from .util import cosine, jaccard, rank_and_winners


def _join(vals):
    vals = [str(v) for v in vals]
    return "; ".join(vals)


def round_results(s: pd.DataFrame) -> pd.DataFrame:
    cols = ["league", "round", "round_name", "place", "song", "artist", "submitter", "points", "n_voters", "status"]
    scored = s[s["points"].notna()].sort_values(["round", "place", "song"])
    return scored[scored["place"] <= 3][cols].reset_index(drop=True)


def leaderboard(s: pd.DataFrame) -> pd.DataFrame:
    sc = s[s["points"].notna() & s["submitter"].notna()]
    g = sc.groupby("submitter")
    out = pd.DataFrame({
        "submissions": g.size(),
        "official_points": g["points"].sum(),
        "wins": g["place"].apply(lambda x: int((x == 1).sum())),
        "podiums": g["place"].apply(lambda x: int((x <= 3).sum())),
        "forfeited_songs": g["status"].apply(lambda x: int((x == "Forfeited").sum())),
        "raw_vote_points": g["raw_points"].sum(),
    })
    out["avg_points_per_submission"] = out["official_points"] / out["submissions"]
    out["points_lost_to_forfeits"] = out["raw_vote_points"] - out["official_points"]
    out = out.reset_index().sort_values(["official_points", "wins"], ascending=[False, False]).reset_index(drop=True)
    out.insert(0, "rank", out["official_points"].rank(method="min", ascending=False).astype(int))
    return out


def song_table(s: pd.DataFrame) -> pd.DataFrame:
    t = s.copy()
    t["avg_points_positive_voters"] = np.where(t["raw_voters"] > 0, t["raw_points"] / t["raw_voters"].replace(0, np.nan), np.nan)
    t["avg_points_eligible"] = np.where(t["elig"] > 0, t["raw_points"] / t["elig"].replace(0, np.nan), np.nan)
    t["share_eligible_voting"] = np.where(t["elig"] > 0, t["raw_voters"] / t["elig"].replace(0, np.nan), np.nan)
    keep = ["league", "round", "round_name", "song", "artist", "submitter", "genre", "major_genre", "subgenre", "place",
            "points", "n_voters", "raw_points", "raw_voters", "elig", "avg_points_positive_voters", "avg_points_eligible",
            "share_eligible_voting", "norm", "round_pct", "round_size", "status", "uri"]
    return t[keep]


def top_songs(st: pd.DataFrame, cfg: Config):
    base = st[st["elig"] > 0].copy()
    base["place_sort"] = base["place"].fillna(9999)
    a, _, _ = rank_and_winners(base, [("raw_points", False), ("raw_voters", False), ("avg_points_eligible", False),
                                      ("place_sort", True), ("song", True), ("artist", True)], cfg.tie_tolerance)
    b, _, _ = rank_and_winners(base, [("avg_points_eligible", False), ("raw_voters", False), ("raw_points", False),
                                      ("place_sort", True), ("song", True), ("artist", True)], cfg.tie_tolerance)
    return a.head(cfg.top_n).drop(columns="place_sort"), b.head(cfg.top_n).drop(columns="place_sort")


def fans(s: pd.DataFrame, v: pd.DataFrame):
    vm = v.merge(s[["song_idx", "song", "status"]], on="song_idx")
    pair = vm.groupby(["submitter", "voter"]).agg(points=("points", "sum"), songs_scored=("song_idx", "nunique")).reset_index()
    total = pair.groupby("submitter")["points"].sum().rename("total_received")
    forf = s[s["status"] == "Forfeited"].groupby("submitter").size().rename("forfeited_songs")
    rows = []
    for sub, g in pair.groupby("submitter"):
        d, w, status = rank_and_winners(g, [("points", False)])
        rows.append(dict(submitter=sub, biggest_fan=_join(w["voter"]), tie=status == "co-winners",
                         fan_points=int(w["points"].iloc[0]), songs_scored_by_fan=int(w["songs_scored"].iloc[0]),
                         avg_points_per_scored_song=float(w["points"].iloc[0] / w["songs_scored"].iloc[0]),
                         share_of_received=float(w["points"].iloc[0] / total[sub]),
                         total_received=int(total[sub])))
    out = pd.DataFrame(rows)
    out["forfeited_songs"] = out["submitter"].map(forf).fillna(0).astype(int)
    matrix = pair.pivot(index="voter", columns="submitter", values="points").fillna(0).astype(int)
    return out.sort_values("submitter").reset_index(drop=True), pair, matrix


def twins(s: pd.DataFrame, v: pd.DataFrame, b: pd.DataFrame, cfg: Config):
    songs = s[s["elig"] > 0].reset_index(drop=True)
    voters = sorted(b["voter"].unique())
    vi = {x: i for i, x in enumerate(voters)}
    ballot = {k: set(g["voter"]) for k, g in b.groupby("round")}
    M = np.full((len(voters), len(songs)), np.nan)
    sidx = {int(i): j for j, i in enumerate(songs["song_idx"])}
    for j, r in songs.iterrows():
        for vo in ballot.get(r["round"], set()) - {r["submitter"]}:
            M[vi[vo], j] = 0.0
    for r in v.itertuples():
        if r.song_idx in sidx:
            M[vi[r.voter], sidx[r.song_idx]] = r.points
    srounds = songs["round"].to_numpy()
    wc, wj = cfg.twin_weights
    rows = []
    for a in voters:
        for c in voters:
            if a == c:
                continue
            xa, xc = M[vi[a]], M[vi[c]]
            mask = ~np.isnan(xa) & ~np.isnan(xc)
            both_rounds = sum(1 for r in ballot if a in ballot[r] and c in ballot[r])
            row = dict(voter=a, other=c, shared_rounds=both_rounds, shared_songs=int(mask.sum()),
                       cosine=np.nan, jaccard=np.nan, combined=np.nan, status="ok")
            pa, pc = xa[mask], xc[mask]
            if both_rounds < cfg.twin_min_shared_rounds:
                row["status"] = "insufficient shared rounds"
            elif not (pa.any() and pc.any()):
                row["status"] = "no positive votes in shared songs"
            else:
                row["cosine"] = cosine(pa, pc)
                row["jaccard"] = jaccard(pa, pc)
                row["combined"] = wc * row["cosine"] + wj * row["jaccard"]
            rows.append(row)
    pairs = pd.DataFrame(rows)
    out = []
    for a, g in pairs.groupby("voter"):
        ok = g.dropna(subset=["combined"]).sort_values(["combined", "shared_rounds"], ascending=[False, False]).reset_index(drop=True)
        if ok.empty:
            out.append(dict(voter=a, twin=None, twin_combined=np.nan, note="insufficient comparable data"))
            continue
        top = ok.iloc[0]
        ties = ok[np.isclose(ok["combined"], top["combined"], atol=cfg.tie_tolerance)]
        margin = float(top["combined"] - ok.iloc[1]["combined"]) if len(ok) > 1 else np.nan
        near = bool(len(ties) > 1 or (not np.isnan(margin) and margin < cfg.twin_near_tie_margin))
        if len(ties) == 1 and top["shared_rounds"] >= 6 and (np.isnan(margin) or margin >= cfg.twin_near_tie_margin):
            conf = "High"
        elif top["shared_rounds"] >= cfg.twin_min_shared_rounds and (np.isnan(margin) or margin >= 0.01):
            conf = "Medium"
        else:
            conf = "Low"
        # shared positively scored songs with both voters' points
        xa, xc = M[vi[a]], M[vi[top["other"]]]
        both = [(songs.at[j, "song"], int(xa[j]), int(xc[j])) for j in range(len(songs))
                if not np.isnan(xa[j]) and not np.isnan(xc[j]) and xa[j] > 0 and xc[j] > 0]
        both.sort(key=lambda t: (-(t[1] + t[2]), t[0]))
        rec = dict(voter=a, twin=_join(ties["other"]), tie=len(ties) > 1, twin_combined=float(top["combined"]),
                   twin_cosine=float(top["cosine"]), twin_jaccard=float(top["jaccard"]),
                   shared_rounds=int(top["shared_rounds"]), shared_songs=int(top["shared_songs"]),
                   runner_up=ok.iloc[len(ties)]["other"] if len(ok) > len(ties) else None,
                   runner_up_combined=float(ok.iloc[len(ties)]["combined"]) if len(ok) > len(ties) else np.nan,
                   margin_to_runner_up=margin, near_tie=near, confidence=conf,
                   shared_positive_songs=len(both),
                   top_shared_songs="; ".join(f"{t[0]} ({a} {t[1]}, {top['other']} {t[2]})" for t in both[:3]),
                   note="")
        out.append(rec)
    cols = ["voter", "twin", "tie", "twin_combined", "twin_cosine", "twin_jaccard", "shared_rounds", "shared_songs", "runner_up",
            "runner_up_combined", "margin_to_runner_up", "near_tie", "confidence", "shared_positive_songs", "top_shared_songs", "note"]
    tw = pd.DataFrame(out).reindex(columns=cols)      # stable schema even when no voter has a comparable twin
    return tw.sort_values("voter").reset_index(drop=True), pairs


def gems(st: pd.DataFrame, cfg: Config):
    base = st[(st["elig"] >= cfg.gem_min_eligible) & (st["raw_voters"] >= cfg.gem_min_positive)
              & (st["round_pct"] >= cfg.gem_min_round_percentile)].copy()
    base["breadth"] = base["raw_voters"] / base["elig"]
    excluded = base[base["status"].isin(["Forfeited", "Mismatch", "Unscored"])]
    pool = base[~base["status"].isin(["Forfeited", "Mismatch", "Unscored"])].copy()

    def score(df, w):
        df = df.copy()
        df["breadth_pctile"] = df["breadth"].rank(pct=True, method="average")
        df["bad_finish_pctile"] = df["round_pct"].rank(pct=True, method="average")
        df["gem_score"] = w[0] * df["breadth_pctile"] + w[1] * df["bad_finish_pctile"]
        return df
    main = score(pool, cfg.gem_weights)
    alt = score(pool, cfg.gem_sensitivity_weights)
    keys = [("gem_score", False), ("avg_points_positive_voters", False), ("elig", False), ("song", True), ("artist", True)]
    mr, _, _ = rank_and_winners(main, keys, cfg.tie_tolerance)
    ar, _, _ = rank_and_winners(alt, keys, cfg.tie_tolerance)
    top = mr.head(cfg.top_n)
    alt_top = ar.head(cfg.top_n)
    key = lambda d: list(zip(d["league"], d["round"], d["uri"]))
    same_members = set(key(top)) == set(key(alt_top))
    same_order = key(top) == key(alt_top)
    top = top.assign(in_top_at_alt_weights=[k in set(key(alt_top)) for k in key(top)])
    summary = dict(pool_size=len(pool), top_n=len(top), same_members_at_alt_weights=same_members, same_order_at_alt_weights=same_order)
    return top, mr, excluded, summary


def genre_summary(s: pd.DataFrame, col: str, top_n: int) -> pd.DataFrame:
    d = s[s[col].notna()]
    if d.empty:
        return pd.DataFrame()
    scored = d[(d["points"].notna()) & (d["status"] == "OK")]
    g = d.groupby(col)
    out = pd.DataFrame({
        "songs": g.size(),
        "distinct_submitters": g["submitter"].nunique(),
        "total_official_points": g["points"].sum(),
    })
    out["share_of_songs"] = out["songs"] / out["songs"].sum()
    out["avg_points_per_scored_song"] = scored.groupby(col)["points"].mean()
    out["avg_normalized_score"] = scored.groupby(col)["norm"].mean()
    out = out.reset_index().rename(columns={col: "label"})
    out.insert(0, "dimension", col)
    out = out.sort_values(["songs", "total_official_points", "avg_points_per_scored_song", "label"],
                          ascending=[False, False, False, True]).reset_index(drop=True)
    out["popularity_rank"] = np.arange(1, len(out) + 1)
    out["top_n"] = out["popularity_rank"] <= top_n
    return out


def profiles(s: pd.DataFrame, v: pd.DataFrame, b: pd.DataFrame, rounds: pd.DataFrame, fans_df, twins_df):
    vm = v.merge(s[["song_idx", "song", "artist", "genre", "major_genre", "subgenre", "submitter", "round_name"]]
                 .rename(columns={"submitter": "song_submitter"}), on="song_idx")
    people = sorted(set(s["submitter"].dropna()) | set(v["voter"]))
    subs = s[s["submitter"].notna()][["league", "submitter", "round", "round_name", "song", "artist", "genre", "major_genre",
                                      "subgenre", "place", "points", "status"]].sort_values(["submitter", "round"])
    top_rows, support_rows, mix_rows, summary = [], [], [], []
    all_rounds = sorted(rounds["round"].unique())
    for p in people:
        mine = vm[vm["voter"] == p].sort_values(["points", "song"], ascending=[False, True])
        if len(mine):
            cutoff = mine["points"].iloc[min(4, len(mine) - 1)]
            for i, r in enumerate(mine[mine["points"] >= cutoff].itertuples(), 1):
                top_rows.append(dict(person=p, song=r.song, artist=r.artist, submitter=r.song_submitter, points_given=r.points,
                                     round_name=r.round_name))
        total = mine["points"].sum()
        for dim, col in [("artist", "artist"), ("submitter", "song_submitter"), ("genre", "genre"),
                         ("major_genre", "major_genre"), ("subgenre", "subgenre")]:
            if total and mine[col].notna().any():
                g = mine.groupby(col)["points"].sum().sort_values(ascending=False)
                for lab, pts in g.items():
                    support_rows.append(dict(person=p, dimension=dim, label=lab, points_given=int(pts), share=pts / total))
        sp = s[s["submitter"] == p]
        for dim in ["genre", "major_genre", "subgenre"]:
            sub_share = sp[dim].dropna().value_counts(normalize=True) if sp[dim].notna().any() else pd.Series(dtype=float)
            rew = mine.groupby(dim)["points"].sum() / total if total and mine[dim].notna().any() else pd.Series(dtype=float)
            for lab in sorted(set(sub_share.index) | set(rew.index)):
                a_, b_ = float(sub_share.get(lab, 0.0)), float(rew.get(lab, 0.0))
                mix_rows.append(dict(person=p, dimension=dim, label=lab, submitted_share=a_, rewarded_share=b_, difference=b_ - a_))
        have = set(sp["round"])
        mj = mine.groupby("major_genre")["points"].sum().sort_values(ascending=False) if total else pd.Series(dtype=float)
        ms = mine.groupby("song_submitter")["points"].sum().sort_values(ascending=False) if total else pd.Series(dtype=float)
        fan = fans_df.loc[fans_df["submitter"] == p, "biggest_fan"]
        tw = twins_df.loc[twins_df["voter"] == p, "twin"]
        summary.append(dict(person=p, submissions=len(sp), ballots=int((b["voter"] == p).sum()), points_given=int(total),
                            missing_rounds=_join([r for r in all_rounds if r not in have]),
                            top2_major_genre_share=float(mj.head(2).sum() / total) if total else np.nan,
                            major_genres_supported=int(len(mj)), most_supported_submitter=ms.index[0] if len(ms) else None,
                            biggest_fan=fan.iloc[0] if len(fan) else None, taste_twin=tw.iloc[0] if len(tw) else None))
    return (subs.reset_index(drop=True), pd.DataFrame(top_rows), pd.DataFrame(support_rows),
            pd.DataFrame(mix_rows), pd.DataFrame(summary))


def analyze_league(ds: Dataset, n: int, cfg: Config) -> dict:
    s = ds.songs[ds.songs["league"] == n].copy()
    if s.empty:
        raise ValueError(f"League {n} not found. Available: {ds.leagues()}")
    v = ds.votes[ds.votes["league"] == n].copy()
    b = ds.ballots[ds.ballots["league"] == n].copy()
    rnd = ds.rounds[ds.rounds["league"] == n].copy()
    out: dict = {}
    has_votes = len(v) > 0
    out["round_results"] = round_results(s)
    out["leaderboard"] = leaderboard(s)
    st = song_table(s)
    out["songs"] = st
    summary = dict(league=n, league_label=s["league_label"].iloc[0], rounds=int(rnd["round"].nunique()),
                   scored_rounds=int(rnd["scored"].sum()), songs=len(s), vote_rows=len(v), vote_points=int(v["points"].sum()) if has_votes else 0,
                   mode="full" if has_votes else "partial (no votes)", cap_known_rounds=int(rnd["cap_known"].sum()))
    if has_votes:
        t_total, t_avg = top_songs(st, cfg)
        out["top_songs_total_points"], out["top_songs_avg_per_eligible_voter"] = t_total, t_avg
        fdf, pair, matrix = fans(s, v)
        out["fans"], out["fan_pairs"], out["fan_matrix"] = fdf, pair, matrix.reset_index()
        tw, pairs = twins(s, v, b, cfg)
        out["twins"], out["twin_pairs"] = tw, pairs
        g_top, g_rank, g_excl, gsum = gems(st, cfg)
        out["gems"], out["gems_ranked"], out["gems_excluded_forfeit"] = g_top, g_rank, g_excl
        summary["gems"] = gsum
    else:
        fdf = pd.DataFrame(columns=["submitter", "biggest_fan"]); tw = pd.DataFrame(columns=["voter", "twin"])
    gs = [genre_summary(s, c, cfg.top_n) for c in ("genre", "major_genre", "subgenre")]
    out["genre_summary"] = pd.concat([g for g in gs if len(g)], ignore_index=True) if any(len(g) for g in gs) else pd.DataFrame()
    if has_votes:
        a, bb, c, d, e = profiles(s, v, b, rnd, fdf, tw)
        out["profile_submissions"], out["profile_top_votes"], out["profile_support"], out["profile_mix"], out["profile_summary"] = a, bb, c, d, e
    # ---- QC ----
    qc = []
    def chk(name, got, expected):
        qc.append(dict(check=name, value=got, expected=expected, status="PASS" if got == expected else "FAIL"))
    if has_votes:
        vp = int(v["points"].sum())
        chk("Song raw points sum = vote points", int(s["raw_points"].sum()), vp)
        chk("Fan matrix sum = vote points", int(out["fan_matrix"].drop(columns="voter").to_numpy().sum()), vp)
        chk("Ballot points sum = vote points", int(b["points"].sum()), vp)
    chk("Only league rows included", int((s["league"] != n).sum()), 0)
    chk("Statuses classified for every song", int(s["status"].isna().sum()), 0)
    out["qc"] = pd.DataFrame(qc)
    out["_summary"] = summary
    return out
