"""Year recap awards. Each award returns winners, a ranked table, the ineligible list and the thresholds used."""
from __future__ import annotations
import re
from collections import Counter
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

from .config import Config
from .data import Dataset
from .util import pielou, rank_and_winners, title_words

STOP = set("""a an and are as at be been but by do does for from had has have he her his i if in into is it its me my no not of
on or our she so than that the their them then there these they this to too up us was we were what when where which who will
with you your am im ill id ive youre dont cant wont didnt isnt aint""".split())
NOISE = set("feat featuring ft with remaster remastered version edit radio mix remix live single original cast recording soundtrack".split())


@dataclass
class Award:
    key: str
    title: str
    purpose: str
    status: str = "winner"              # winner | co-winners | optional | no eligible players | chart
    winners: list = field(default_factory=list)
    headline: str = ""
    notes: list = field(default_factory=list)
    thresholds: dict = field(default_factory=dict)
    table: pd.DataFrame | None = None
    extra_tables: dict = field(default_factory=dict)
    ineligible: pd.DataFrame | None = None

    def to_dict(self) -> dict:
        return dict(key=self.key, title=self.title, purpose=self.purpose, status=self.status, winners=self.winners,
                    headline=self.headline, notes=self.notes, thresholds=self.thresholds,
                    rows=0 if self.table is None else len(self.table))


class Ctx:
    def __init__(self, ds: Dataset, leagues: list, cfg: Config):
        self.cfg = cfg
        self.leagues = leagues
        sc = ds.songs[ds.songs["league"].isin(leagues)]
        self.S = sc[sc["points"].notna() & sc["submitter"].notna()].copy()                  # all scored submissions
        self.perf = self.S[~self.S["status"].isin(cfg.performance_excluded_statuses)].copy()  # performance subset
        self.V = ds.votes[ds.votes["league"].isin(leagues)].copy()
        self.B = ds.ballots[ds.ballots["league"].isin(leagues)].copy()
        self.R = ds.rounds[ds.rounds["league"].isin(leagues)].copy()
        self.songs_all = sc
        self.vm = self.V.merge(sc[["song_idx", "song", "artist", "genre", "major_genre", "round_name", "cap", "cap_known"]], on="song_idx")
        self.vm = self.vm.rename(columns={"submitter": "song_submitter"})
        self.players = sorted(set(self.S["submitter"]) | set(self.V["voter"]))
        self.cap_all_known = bool(self.R["cap_known"].all())

    def excluded_counts(self):
        return self.S["status"].value_counts().to_dict()


def _w(w):  # list of winners
    return [str(x) for x in w]


def _none(key, title, purpose, ineligible=None, note="No eligible data for this award."):
    return Award(key, title, purpose, "no eligible players", [], "", [note], ineligible=ineligible)


def _inelig(counts: pd.Series, minimum: int, label: str) -> pd.DataFrame:
    d = counts[counts < minimum].rename(label).reset_index()
    d.columns = ["player", label]
    d["minimum"] = minimum
    return d


# ---------------------------------------------------------------- awards
def overall_champion(c: Ctx) -> Award:
    S, cfg = c.S, c.cfg
    if S.empty:
        return _none("overall_champion", "Overall Champion", "Strongest cumulative performance across the year", note="No scored submissions.")
    g = S.groupby("submitter")
    t = pd.DataFrame({"total_points": g["points"].sum(), "submissions": g.size(),
                      "round_wins": g["place"].apply(lambda x: int((x == 1).sum())),
                      "podiums": g["place"].apply(lambda x: int((x <= 3).sum())),
                      "avg_place": g["place"].mean(), "raw_vote_points": g["raw_points"].sum(),
                      "forfeited_songs": g["status"].apply(lambda x: int((x == "Forfeited").sum()))})
    t["avg_points_per_submission"] = t["total_points"] / t["submissions"]
    t["normalized_sum"] = c.perf.groupby("submitter")["norm"].sum().reindex(t.index).fillna(0)
    t = t.reset_index().rename(columns={"submitter": "player"})
    ranked, w, status = rank_and_winners(t, [("total_points", False), ("normalized_sum", False), ("round_wins", False), ("avg_place", True)], cfg.tie_tolerance)
    a = Award("overall_champion", "Overall Champion", "Strongest cumulative performance across the year", status, _w(w["player"]),
              f"{' & '.join(_w(w['player']))}: {w['total_points'].iloc[0]:.0f} points over {w['submissions'].iloc[0]} submissions "
              f"({w['avg_points_per_submission'].iloc[0]:.2f} per submission)", table=ranked,
              thresholds={"tie_breakers": "normalized sum, round wins, average place, then co-champions"})
    a.notes.append("Players in more rounds have a cumulative advantage: compare total points with points per submission.")
    a.notes.append("Official points: forfeited songs count as zero, as on the platform.")
    return a


def highest_scoring_song(c: Ctx) -> Award:
    S = c.S
    if S.empty:
        return _none("highest_scoring_song", "Highest Scoring Song", "Single submission with the most points", note="No scored submissions.")
    d = S[["league", "round", "round_name", "song", "artist", "submitter", "points", "raw_voters", "elig", "norm", "status"]].copy()
    d["share_of_available_points"] = d["norm"]
    d["supporters_pct"] = d["raw_voters"] / d["elig"].replace(0, np.nan)
    d = d.rename(columns={"points": "total_points", "raw_voters": "supporters"})
    by_pts, w1, s1 = rank_and_winners(d, [("total_points", False), ("share_of_available_points", False)], c.cfg.tie_tolerance)
    by_share, w2, s2 = rank_and_winners(d.dropna(subset=["share_of_available_points"]), [("share_of_available_points", False), ("total_points", False)], c.cfg.tie_tolerance)
    share_txt = (lambda x: f"{x:.1%}") if c.cap_all_known else (lambda x: f"{x:.2f} points per eligible voter")
    lab = lambda w: " & ".join(f"{r.song} ({r.artist}, {r.submitter}, L{r.league} R{r.round})" for r in w.itertuples())
    a = Award("highest_scoring_song", "Highest Scoring Song", "Single submission with the most points in one round",
              "winner" if s1 == "winner" else "co-winners", [f"{r.song} - {r.submitter}" for r in w1.itertuples()],
              f"Highest raw: {lab(w1)} with {w1['total_points'].iloc[0]:.0f} points. Highest share of available points: {lab(w2)} "
              f"({share_txt(w2['share_of_available_points'].iloc[0])}).", table=by_pts.head(10), extra_tables={"by_share": by_share.head(10)})
    if not c.cap_all_known:
        a.notes.append("Max Votes per Song is blank for some rounds, so share of available points is points per eligible voter (approximate).")
    return a


def one_hit_wonder(c: Ctx) -> Award:
    cfg, S, P = c.cfg, c.S, c.perf
    league_med = P["norm"].median()
    rows = []
    n_perf = P.groupby("submitter").size()
    for p, g in P.groupby("submitter"):
        wins = int((S[S["submitter"] == p]["place"] == 1).sum())
        if len(g) < cfg.min_submissions_award or wins < 1 or len(g) < 2:
            continue
        best = g.loc[g["norm"].idxmax()]
        others = g.drop(index=best.name)
        oth_pts = others["points"].mean()
        rows.append(dict(player=p, submissions=len(g), round_wins=wins, best_song=best["song"], best_round=f"L{best['league']} R{best['round']} {best['round_name']}",
                         best_points=best["points"], best_normalized=best["norm"], other_avg_points=oth_pts, other_avg_normalized=others["norm"].mean(),
                         one_hit_gap=best["points"] - oth_pts, one_hit_ratio=(best["points"] / oth_pts) if oth_pts > 0 else np.nan,
                         one_hit_index=best["norm"] - others["norm"].mean(), best_vs_league_median_normalized=best["norm"] - league_med,
                         others_avg_round_percentile=others["round_pct"].mean(),
                         best_supporters=int(best["raw_voters"]), best_supporters_pct=best["raw_voters"] / best["elig"]))
    t = pd.DataFrame(rows)
    inel = _inelig(n_perf, cfg.min_submissions_award, "performance_submissions")
    if t.empty:
        return Award("one_hit_wonder", "One-Hit Wonder", "One dominant round, weaker elsewhere", "no eligible players", ineligible=inel)
    ranked, w, status = rank_and_winners(t, [("one_hit_index", False), ("best_normalized", False)], cfg.tie_tolerance)
    r = w.iloc[0]
    a = Award("one_hit_wonder", "One-Hit Wonder", "One dominant round, weaker elsewhere", status, _w(w["player"]),
              f"{r['player']}: '{r['best_song']}' ({r['best_points']:.0f} pts) vs {r['other_avg_points']:.1f} average elsewhere; index {r['one_hit_index']:.2f}",
              table=ranked, ineligible=inel,
              thresholds={"min_submissions": cfg.min_submissions_award, "min_round_wins": 1, "primary": "one_hit_index"})
    a.notes.append("Index (best normalized minus mean of other normalized) is primary. Ratio is shown only when the other average is above zero.")
    a.notes.append("Forfeited, zero-vote, mismatched and unscored songs are excluded from performance measures.")
    return a


def consistency(c: Ctx) -> Award:
    cfg, P = c.cfg, c.perf
    g = P.groupby("submitter")
    t = pd.DataFrame({"submissions_counted": g.size(), "avg_points": g["points"].mean(), "avg_normalized": g["norm"].mean(),
                      "sd_normalized": g["norm"].std(ddof=1)})
    inel = _inelig(t["submissions_counted"], cfg.min_submissions_award, "submissions_counted")
    t = t[t["submissions_counted"] >= cfg.min_submissions_award].copy()
    t["consistency_score"] = t["avg_normalized"] - t["sd_normalized"]
    t = t.reset_index().rename(columns={"submitter": "player"})
    if t.empty:
        return Award("consistency", "Consistency", "Steady scores", "no eligible players", ineligible=inel)
    ranked, w, status = rank_and_winners(t, [("consistency_score", False), ("submissions_counted", False)], cfg.tie_tolerance)
    r = w.iloc[0]
    a = Award("consistency", "Consistency", "Highest average normalized score with the least variation", status, _w(w["player"]),
              f"{r['player']}: average {r['avg_normalized']:.2f}, SD {r['sd_normalized']:.2f}, score {r['consistency_score']:.2f} over {r['submissions_counted']} submissions",
              table=ranked, ineligible=inel, thresholds={"min_submissions": cfg.min_submissions_award, "sd": "sample SD of normalized scores"})
    a.notes.append("Score = mean normalized score minus the sample standard deviation of normalized scores (same units).")
    a.notes.append("Short-tenure players can top this award: check submissions_counted.")
    return a


def vote_spread(c: Ctx) -> Award:
    v = c.V
    rows = []
    for scope, d in [("all", v)] + [(f"league_{n}", v[v["league"] == n]) for n in c.leagues]:
        vc = d["points"].value_counts().sort_index()
        for val, cnt in vc.items():
            rows.append(dict(scope=scope, point_value=int(val), votes=int(cnt), pct=cnt / len(d)))
    t = pd.DataFrame(rows)
    allv = t[t["scope"] == "all"]
    a = Award("vote_spread", "Vote Spread", "How often each point value was awarded", "chart", [],
              "Point values awarded: " + ", ".join(f"{r.point_value}: {r.votes} ({r.pct:.1%})" for r in allv.itertuples()),
              table=t, thresholds={"only_observed_values": True})
    a.notes.append("Only positive votes are stored; zero-point votes are not in the workbook.")
    return a


def genre_breakdown(c: Ctx) -> Award:
    cfg, S, P = c.cfg, c.S, c.perf
    t = S.groupby("major_genre").agg(submissions=("song_idx", "size"), round_winning=("place", lambda x: int((x == 1).sum()))).reset_index()
    t["submission_share"] = t["submissions"] / t["submissions"].sum()
    t["avg_normalized_score"] = t["major_genre"].map(P.groupby("major_genre")["norm"].mean())
    t["genre_win_rate"] = t["round_winning"] / t["submissions"]
    t = t.sort_values("submissions", ascending=False).reset_index(drop=True)
    sub_counts = S.groupby("submitter").size()
    fp = []
    for p in sub_counts[sub_counts >= cfg.min_submissions_award].index:
        mine_s = S[S["submitter"] == p]["major_genre"].value_counts(normalize=True)
        mine_v = c.vm[c.vm["voter"] == p].groupby("major_genre")["points"].sum()
        mine_v = mine_v / mine_v.sum() if mine_v.sum() else mine_v
        for gname in sorted(set(mine_s.index) | set(mine_v.index)):
            a_, b_ = float(mine_s.get(gname, 0)), float(mine_v.get(gname, 0))
            fp.append(dict(player=p, major_genre=gname, submission_genre_share=a_, voting_genre_share=b_, gap=b_ - a_))
    top = t.head(3)
    a = Award("genre_breakdown", "Genre Breakdown", "What the group submitted vs what performed; each player's submit-vs-reward fingerprint", "chart", [],
              "Most submitted: " + ", ".join(f"{r.major_genre} ({r.submission_share:.1%})" for r in top.itertuples()),
              table=t, extra_tables={"player_fingerprint": pd.DataFrame(fp)},
              thresholds={"fingerprint_min_submissions": cfg.min_submissions_award})
    a.notes.append("Genres are the workbook's Major Genre labels (curated mapping), kept separate from voting results.")
    return a


def you_know_who(c: Ctx) -> Award:
    cfg, S = c.cfg, c.S
    rows, subs = [], S.groupby("submitter").size()
    for p, g in S.groupby("submitter"):
        if len(g) < cfg.min_submissions_award:
            continue
        vc = g["major_genre"].value_counts()
        rows.append(dict(player=p, submissions=len(g), top_genre=vc.index[0], top_genre_count=int(vc.iloc[0]), concentration=vc.iloc[0] / len(g)))
    inel = _inelig(subs, cfg.min_submissions_award, "submissions")
    if not rows:
        return Award("you_know_who", "You Know Who", "Most associated with one genre", "no eligible players", ineligible=inel)
    t = pd.DataFrame(rows)
    ranked, w, status = rank_and_winners(t, [("concentration", False), ("top_genre_count", False)], cfg.tie_tolerance)
    cnt_rank, wc, _ = rank_and_winners(t, [("top_genre_count", False), ("concentration", False)], cfg.tie_tolerance)
    r = w.iloc[0]
    a = Award("you_know_who", "You Know Who", "Player most associated with one major genre", status, _w(w["player"]),
              f"Of {r['player']}'s submissions, {r['concentration']:.0%} landed in {r['top_genre']}, the highest concentration in the league.",
              table=ranked, extra_tables={"by_count": cnt_rank}, ineligible=inel, thresholds={"min_submissions": cfg.min_submissions_award, "primary": "concentration"})
    a.notes.append("Highest count winner (secondary view): " + ", ".join(_w(wc["player"])))
    return a


def genre_explorer(c: Ctx) -> Award:
    cfg, S = c.cfg, c.S
    rows = []
    for p, g in S.groupby("submitter"):
        if len(g) < cfg.min_submissions_award:
            continue
        vc = g["major_genre"].value_counts()
        rows.append(dict(player=p, distinct_major_genres=len(vc), submissions=len(g), evenness=pielou(vc.values), genres=", ".join(vc.index)))
    inel = _inelig(S.groupby("submitter").size(), cfg.min_submissions_award, "submissions")
    if not rows:
        return Award("genre_explorer", "Genre Explorer", "Widest range of major genres", "no eligible players", ineligible=inel)
    ranked, w, status = rank_and_winners(pd.DataFrame(rows), [("distinct_major_genres", False), ("evenness", False), ("submissions", False)], cfg.tie_tolerance)
    r = w.iloc[0]
    return Award("genre_explorer", "Genre Explorer", "Widest range of major genres", status, _w(w["player"]),
                 f"{r['player']}: {r['distinct_major_genres']} major genres across {r['submissions']} submissions (evenness {r['evenness']:.2f})",
                 table=ranked, ineligible=inel, thresholds={"min_submissions": cfg.min_submissions_award, "evenness": "Pielou H/ln(k)"})


def podium_throne(c: Ctx) -> Award:
    cfg, S = c.cfg, c.S
    rows = []
    for p, g in S.groupby("submitter"):
        if len(g) < cfg.min_submissions_award:
            continue
        gold, silver, bronze = (int((g["place"] == k).sum()) for k in (1, 2, 3))
        rows.append(dict(player=p, submissions=len(g), gold=gold, silver=silver, bronze=bronze, podiums=gold + silver + bronze,
                         weighted_score=3 * gold + 2 * silver + bronze))
    inel = _inelig(S.groupby("submitter").size(), cfg.min_submissions_award, "submissions")
    if not rows:
        return _none("podium_throne", "Podium Throne", "Most trips to the top three", inel)
    ranked, w, status = rank_and_winners(pd.DataFrame(rows), [("weighted_score", False), ("gold", False)], cfg.tie_tolerance)
    r = w.iloc[0]
    a = Award("podium_throne", "Podium Throne", "Most trips to the top three", status, _w(w["player"]),
              f"{r['player']}: weighted {r['weighted_score']} ({r['gold']} gold, {r['silver']} silver, {r['bronze']} bronze)",
              table=ranked, ineligible=inel, thresholds={"min_submissions": cfg.min_submissions_award, "weights": "3/2/1"})
    a.notes.append("Tied songs share a place (competition ranking: a tie for first means no second place).")
    return a


def blowout_squeaker(c: Ctx) -> Award:
    rows, ties = [], []
    for (l, r), g in c.S.groupby(["league", "round"]):
        g = g.sort_values(["place", "points"], ascending=[True, False])
        if len(g) < 2:
            continue
        top, second = g.iloc[0], g.sort_values("points", ascending=False).iloc[1]
        pts = g.sort_values("points", ascending=False)["points"].tolist()
        margin = pts[0] - pts[1]
        denom = top["elig"] * top["cap"]
        row = dict(league=l, round=r, round_name=top["round_name"], winning_song=top["song"], artist=top["artist"], submitter=top["submitter"],
                   first_points=pts[0], second_points=pts[1], margin=margin, margin_pct=margin / denom if denom else np.nan, eligible_voters=int(top["elig"]))
        if margin == 0:
            ties.append(dict(row, official_winner=top["song"], tied_score=pts[0], tied_songs=int((g["points"] == pts[0]).sum())))
        else:
            rows.append(row)
    t = pd.DataFrame(rows)
    ties = pd.DataFrame(ties)
    cfg = c.cfg
    if t.empty:
        return _none("blowout_squeaker", "Blowout vs. Squeaker", "Most decisive vs closest round win", note="No round has a positive winning margin.")
    big, wb, sb = rank_and_winners(t, [("margin_pct", False), ("margin", False)], cfg.tie_tolerance)
    sq, wq, sq_s = rank_and_winners(t, [("margin_pct", True), ("margin", True)], cfg.tie_tolerance)
    f = lambda w: " & ".join(f"{r.winning_song} (L{r.league} R{r.round}, margin {r.margin:.0f}, {r.margin_pct:.1%})" for r in w.itertuples())
    a = Award("blowout_squeaker", "Blowout vs. Squeaker", "Most decisive vs closest round win", "winner" if sb == "winner" and sq_s == "winner" else "co-winners",
              [f"Blowout: {x}" for x in _w(wb["winning_song"])] + [f"Squeaker: {x}" for x in _w(wq["winning_song"])],
              f"Blowout: {f(wb)}. Squeaker: {f(wq)}.", table=big, extra_tables={"squeaker_ranked": sq, "tied_first_place_rounds": ties},
              thresholds={"completed_rounds_only": True})
    a.notes.append(f"{len(ties)} rounds had a tied first-place score; they are listed separately with the official winner.")
    if not c.cap_all_known:
        a.notes.append("Margin % uses points per eligible voter where Max Votes per Song is blank (approximate).")
    return a


def generosity(c: Ctx) -> Award:
    cfg = c.cfg
    S_all = c.songs_all
    size = S_all.groupby(["league", "round"]).size()
    own = S_all.groupby(["league", "round", "submitter"]).size()
    top = c.V.groupby(["league", "round", "voter"])["points"].max()
    mode_budget = c.R["budget"].mode().iloc[0] if c.R["budget"].notna().any() else np.nan
    bud = c.R.set_index(["league", "round"])["budget"]
    rows = []
    for b in c.B.itertuples():
        elig_songs = size[(b.league, b.round)] - own.get((b.league, b.round, b.voter), 0)
        rows.append(dict(player=b.voter, league=b.league, round=b.round, supported=b.n_votes, eligible_songs=elig_songs,
                         breadth=b.n_votes / elig_songs if elig_songs else np.nan, top_song_share=top[(b.league, b.round, b.voter)] / b.points,
                         unusual_budget=bool(pd.notna(bud.get((b.league, b.round))) and bud.get((b.league, b.round)) != mode_budget)))
    ballots = pd.DataFrame(rows)
    g = ballots.groupby("player")
    t = pd.DataFrame({"ballots": g.size(), "avg_support_breadth": g["breadth"].mean(), "avg_songs_supported": g["supported"].mean(),
                      "avg_top_song_share": g["top_song_share"].mean(), "ballots_in_unusual_budget_rounds": g["unusual_budget"].sum()}).reset_index()
    inel = _inelig(g.size(), cfg.min_ballots, "ballots")
    t = t[t["ballots"] >= cfg.min_ballots].copy()
    if t.empty:
        return _none("generosity", "Generosity Engine / Very Exclusive Guest List / All-In Voter", "Broad vs concentrated voting", inel)
    e, we, se = rank_and_winners(t, [("avg_support_breadth", False), ("ballots", False), ("avg_songs_supported", False)], cfg.tie_tolerance)
    x, wx, sx = rank_and_winners(t, [("avg_support_breadth", True), ("ballots", False), ("avg_songs_supported", True)], cfg.tie_tolerance)
    ai, wa, sa = rank_and_winners(t, [("avg_top_song_share", False), ("ballots", False)], cfg.tie_tolerance)
    a = Award("generosity", "Generosity Engine / Very Exclusive Guest List / All-In Voter", "Broad vs concentrated voting, measured per ballot", "co-winners" if "co-winners" in (se, sx, sa) else "winner",
              [f"Generosity Engine: {' & '.join(_w(we['player']))}", f"Very Exclusive Guest List: {' & '.join(_w(wx['player']))}", f"All-In Voter: {' & '.join(_w(wa['player']))}"],
              f"Engine {we['player'].iloc[0]} (breadth {we['avg_support_breadth'].iloc[0]:.0%}); Guest List {wx['player'].iloc[0]} ({wx['avg_support_breadth'].iloc[0]:.0%}); "
              f"All-In {wa['player'].iloc[0]} (top-song share {wa['avg_top_song_share'].iloc[0]:.0%}).",
              table=e, extra_tables={"guest_list_order": x, "all_in_order": ai, "ballot_level": ballots}, ineligible=inel,
              thresholds={"min_ballots": cfg.min_ballots})
    a.notes.append("Breadth is computed per ballot, then averaged. Rounds with a non-standard point budget are flagged per player.")
    return a


def _high_votes(c: Ctx):
    cfg = c.cfg
    vm = c.vm.copy()
    vm["high"] = vm["points"] >= cfg.high_vote_threshold
    vm["high_cap"] = np.where(vm["cap_known"], vm["points"] >= cfg.high_vote_cap_share * vm["cap"], np.nan)
    return vm


def times_gave(c: Ctx) -> Award:
    cfg = c.cfg
    if c.vm.empty:
        return _none("times_gave_3plus", f"Times You Gave {cfg.high_vote_threshold}+ Points", "How often each voter gave a strong vote", note="No votes.")
    vm = _high_votes(c)
    g = vm.groupby("voter")
    t = pd.DataFrame({"positive_votes": g.size(), "high_votes_given": g["high"].sum().astype(int),
                      "unique_songs_high": vm[vm["high"]].groupby("voter")["song_idx"].nunique(),
                      "unique_submitters_high": vm[vm["high"]].groupby("voter")["song_submitter"].nunique()}).fillna(0)
    t["high_vote_pct"] = t["high_votes_given"] / t["positive_votes"]
    cap_votes = vm[vm["cap_known"]].groupby("voter")["high_cap"].sum() if vm["cap_known"].any() else None
    if cap_votes is not None:
        t["high_votes_at_30pct_of_max"] = cap_votes
    t = t.reset_index().rename(columns={"voter": "player"})
    by_count, wc, _ = rank_and_winners(t, [("high_votes_given", False), ("high_vote_pct", False)], cfg.tie_tolerance)
    by_pct, wp, _ = rank_and_winners(t, [("high_vote_pct", False), ("high_votes_given", False)], cfg.tie_tolerance)
    a = Award("times_gave_3plus", f"Times You Gave {cfg.high_vote_threshold}+ Points", "How often each voter gave a strong vote", "optional",
              [f"Most: {' & '.join(_w(wc['player']))}", f"Highest rate: {' & '.join(_w(wp['player']))}"],
              f"Most strong votes: {wc['player'].iloc[0]} ({wc['high_votes_given'].iloc[0]}). Highest rate: {wp['player'].iloc[0]} ({wp['high_vote_pct'].iloc[0]:.1%}).",
              table=by_count, extra_tables={"by_rate": by_pct}, thresholds={"points_at_least": cfg.high_vote_threshold})
    if cap_votes is None:
        a.notes.append("The 30%-of-maximum version needs Max Votes per Song on the Rounds tab; it is not available.")
    return a


def times_received(c: Ctx) -> Award:
    cfg = c.cfg
    if c.vm.empty:
        return _none("times_received_3plus", f"Times You Received {cfg.high_vote_threshold}+ Points", "How often a player's songs drew a strong vote", note="No votes.")
    vm = _high_votes(c)
    hv = vm[vm["high"]]
    subs = c.S.groupby("submitter").size()
    t = pd.DataFrame({"submissions": subs, "high_votes_received": hv.groupby("song_submitter").size(),
                      "submissions_with_high_vote": hv.groupby("song_submitter")["song_idx"].nunique(),
                      "unique_high_voters": hv.groupby("song_submitter")["voter"].nunique()}).fillna(0)
    t["high_votes_per_submission"] = t["high_votes_received"] / t["submissions"]
    t = t.reset_index().rename(columns={"index": "player", "submitter": "player"})
    by_count, wc, _ = rank_and_winners(t, [("high_votes_received", False), ("high_votes_per_submission", False)], cfg.tie_tolerance)
    by_rate, wr, _ = rank_and_winners(t, [("high_votes_per_submission", False), ("high_votes_received", False)], cfg.tie_tolerance)
    return Award("times_received_3plus", f"Times You Received {cfg.high_vote_threshold}+ Points", "How often a player's songs drew a strong vote", "optional",
                 [f"Most: {' & '.join(_w(wc['player']))}", f"Highest rate: {' & '.join(_w(wr['player']))}"],
                 f"Most: {wc['player'].iloc[0]} ({int(wc['high_votes_received'].iloc[0])}). Highest per submission: {wr['player'].iloc[0]} ({wr['high_votes_per_submission'].iloc[0]:.2f}).",
                 table=by_count, extra_tables={"by_rate": by_rate}, thresholds={"points_at_least": cfg.high_vote_threshold})


def title_cloud(c: Ctx) -> Award:
    S = c.S
    per_song = [(r.submitter, r.league, title_words(r.song)) for r in S.itertuples()]
    vocab = Counter(w for _, _, ws in per_song for w in ws if w not in STOP and w not in NOISE and len(w) > 1)
    merge = {w: w[:-1] for w in vocab if w.endswith("s") and not w.endswith("ss") and len(w) > 3 and w[:-1] in vocab}
    norm = lambda w: merge.get(w, w)
    rows = []
    def count(scope, items):
        cnt = Counter(norm(w) for ws in items for w in ws if w not in STOP and w not in NOISE and len(w) > 1)
        for w, n in cnt.most_common(30):
            rows.append(dict(scope=scope, word=w, count=n))
        return cnt
    allc = count("all", [ws for _, _, ws in per_song])
    for n in c.leagues:
        count(f"league_{n}", [ws for _, l, ws in per_song if l == n])
    for p in sorted({p for p, _, _ in per_song}):
        count(f"player_{p}", [ws for q, _, ws in per_song if q == p])
    t = pd.DataFrame(rows)
    top = allc.most_common(10)
    a = Award("title_cloud", "Title Cloud", "Most common words in submitted song titles (titles only, no lyrics)", "chart", [],
              "Top words: " + ", ".join(f"{w} ({n})" for w, n in top[:5]), table=t[t["scope"] == "all"].head(10), extra_tables={"all_scopes": t},
              thresholds={"unique_words": len(allc), "most_repeated": top[0][0] if top else None})
    a.notes.append("Cleaning: lowercase, remove (feat. ...), [...], remaster/version suffixes, punctuation, common stop words; word forms merged only when both singular and plural occur.")
    return a


def biggest_fan(c: Ctx) -> Award:
    cfg, S = c.cfg, c.songs_all[c.songs_all["submitter"].notna()]
    ballots = {k: set(g["voter"]) for k, g in c.B.groupby(["league", "round"])}
    cap = c.R.set_index(["league", "round"])["cap"]
    nsongs = S.groupby(["league", "round", "submitter"]).size()
    pts = c.vm.groupby(["song_submitter", "voter"])["points"].sum()
    fav = {}
    for (sub, vo), g in c.vm.groupby(["song_submitter", "voter"]):
        m = g["points"].max()
        fav[(sub, vo)] = "; ".join(sorted(g[g["points"] == m]["song"]))
    rows = []
    for sub in sorted(S["submitter"].unique()):
        mine = nsongs[nsongs.index.get_level_values("submitter") == sub]
        for vo in c.players:
            if vo == sub:
                continue
            shared = [(l, r, n) for (l, r, _), n in mine.items() if vo in ballots.get((l, r), set())]
            if not shared:
                continue
            maxp = sum(n * cap[(l, r)] for l, r, n in shared)
            got = int(pts.get((sub, vo), 0))
            rows.append(dict(submitter=sub, voter=vo, points_given=got, shared_eligible_rounds=len(shared), max_possible=maxp,
                             support_rate=got / maxp if maxp else np.nan, favorite_submission=fav.get((sub, vo), "")))
    allp = pd.DataFrame(rows, columns=["submitter", "voter", "points_given", "shared_eligible_rounds", "max_possible", "support_rate", "favorite_submission"])
    elig = allp[allp["shared_eligible_rounds"] >= cfg.min_shared_rounds_pair]
    if elig.empty:
        return _none("biggest_fan", "Biggest Fan", "Voter with the highest support rate per submitter", note="No voter and submitter share enough eligible rounds.")
    out, ties = [], 0
    for sub, g in elig.groupby("submitter"):
        d, w, st = rank_and_winners(g, [("support_rate", False), ("points_given", False), ("shared_eligible_rounds", False)], cfg.tie_tolerance)
        ties += st == "co-winners"
        r = w.iloc[0]
        out.append(dict(submitter=sub, biggest_fan=" & ".join(_w(w["voter"])), tie=st == "co-winners", points_given=int(r["points_given"]),
                        support_rate=r["support_rate"], shared_eligible_rounds=int(r["shared_eligible_rounds"]),
                        favorite_submission=r["favorite_submission"] if len(w) == 1 else ""))
    t = pd.DataFrame(out)
    a = Award("biggest_fan", "Biggest Fan", "For each submitter, the voter with the highest support rate across shared rounds", "optional", [],
              f"{len(t)} submitters have a biggest fan; {ties} ties.", table=t, extra_tables={"all_pairs": allp},
              thresholds={"min_shared_rounds": cfg.min_shared_rounds_pair, "rate": "points given / (shared rounds x songs x max votes per song)"})
    if not c.cap_all_known:
        a.notes.append("Max Votes per Song is blank for some rounds; rate uses 1 point per song (approximate, ranks voters by average points per shared round).")
    return a


def build_recap(ds: Dataset, leagues: list, cfg: Config) -> dict:
    c = Ctx(ds, leagues, cfg)
    awards = [overall_champion(c), highest_scoring_song(c), one_hit_wonder(c), consistency(c), vote_spread(c), genre_breakdown(c),
              you_know_who(c), genre_explorer(c), podium_throne(c), blowout_squeaker(c), generosity(c), times_gave(c),
              times_received(c), title_cloud(c), biggest_fan(c)]
    scope = dict(leagues=leagues, submissions=len(c.S), votes=len(c.V), players=len(c.players),
                 status_counts=c.excluded_counts(), performance_subset=len(c.perf),
                 performance_excluded_statuses=list(cfg.performance_excluded_statuses), cap_known_all_rounds=c.cap_all_known)
    return dict(awards=awards, scope=scope)
