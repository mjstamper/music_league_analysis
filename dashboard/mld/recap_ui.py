"""Wrapped-style recap: build slides from award tables and render them as story cards.

Slides are plain data (text, chips, optional chart callback). Rendering turns them into HTML cards,
so the same slides power both Story mode (step through) and All awards (gallery).
"""
from __future__ import annotations
import html
import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import altair as alt
import pandas as pd
import streamlit as st

from . import charts

THEMES = [
    ("#0B5D3E", "#1F9D6B"), ("#3A1C71", "#B24592"), ("#1D4E89", "#00A6C0"), ("#7A1F5C", "#E8683A"),
    ("#1B2B27", "#4A6B5F"), ("#4B2A8A", "#7873F5"), ("#0F4C5C", "#D9732B"), ("#8E2C48", "#D96C8A"),
]

CSS = """
<style>
.wrap-card {border-radius: 22px; padding: 34px 38px 30px 38px; color: #fff; margin: 4px 0 14px 0; min-height: 250px;
            box-shadow: 0 6px 22px rgba(0,0,0,.12);}
.wrap-kicker {text-transform: uppercase; letter-spacing: 2.5px; font-size: .78rem; opacity: .85; font-weight: 600;}
.wrap-title {font-size: 3.1rem; line-height: 1.05; font-weight: 800; margin: 10px 0 8px 0; letter-spacing: -1px; word-break: break-word;}
.wrap-title.long {font-size: 2.2rem;}
.wrap-sub {font-size: 1.15rem; opacity: .95; margin-bottom: 18px; max-width: 46rem;}
.wrap-chips {display: flex; flex-wrap: wrap; gap: 12px;}
.wrap-chip {background: rgba(255,255,255,.17); border-radius: 14px; padding: 10px 16px; min-width: 110px;}
.wrap-chip-v {font-size: 1.55rem; font-weight: 700; line-height: 1.1;}
.wrap-chip-l {font-size: .78rem; opacity: .85; margin-top: 2px;}
.wrap-foot {font-size: .85rem; opacity: .8; margin-top: 16px;}
.cloud {display:flex; flex-wrap:wrap; gap:6px 18px; align-items:baseline; justify-content:center; padding: 8px 4px 2px 4px;}
.cloud span {font-weight: 700; line-height: 1.1;}
</style>
"""


@dataclass
class Slide:
    key: str
    kicker: str
    title: str
    subtitle: str = ""
    chips: list = field(default_factory=list)       # [(label, value)]
    theme: int = 0
    footer: str = ""
    extra: Optional[Callable[[], None]] = None      # draws charts/tables under the card
    notes: list = field(default_factory=list)


def esc(x) -> str:
    return html.escape(str(x))


def card_html(s: Slide) -> str:
    a, b = THEMES[s.theme % len(THEMES)]
    chips = "".join(f"<div class='wrap-chip'><div class='wrap-chip-v'>{esc(v)}</div><div class='wrap-chip-l'>{esc(l)}</div></div>" for l, v in s.chips)
    long = " long" if len(s.title) > 24 else ""
    foot = f"<div class='wrap-foot'>{esc(s.footer)}</div>" if s.footer else ""
    return (f"<div class='wrap-card' style='background:linear-gradient(135deg,{a},{b})'>"
            f"<div class='wrap-kicker'>{esc(s.kicker)}</div><div class='wrap-title{long}'>{esc(s.title)}</div>"
            f"<div class='wrap-sub'>{esc(s.subtitle)}</div><div class='wrap-chips'>{chips}</div>{foot}</div>")


def render_slide(s: Slide, show_notes: bool = True):
    st.markdown(card_html(s), unsafe_allow_html=True)
    if s.extra:
        s.extra()
    if show_notes and s.notes:
        with st.expander("How this is calculated"):
            for n in s.notes:
                st.markdown(f"- {n}")


# ---------------------------------------------------------------- helpers
def _tops(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["rank"] == 1] if "rank" in df else df.head(1)


def _names(series) -> str:
    return " & ".join(str(x) for x in series)


def _fmt_num(x, d=0):
    return f"{x:,.{d}f}"


def _cap_known(rd) -> bool:
    return bool(rd.scope.get("cap_known_all_rounds"))


def _notes(rd, key, extra=()):
    out = list(rd.notes(key)) + list(extra)
    th = rd.awards.get(key, {}).get("thresholds") or {}
    if th:
        out.append("Settings: " + ", ".join(f"{k.replace('_', ' ')} = {v}" for k, v in th.items()))
    return out


def _bar(df, y, x, title=None, highlight=None, x_title=None, fmt=None, top=10):
    d = df.head(top).copy()
    d["_hi"] = d[y].isin(highlight) if highlight else False
    d["_c"] = d["_hi"].map({True: "Winner", False: "Others"})
    ch = charts.bar_h(d, y, x, color="_c", color_scale=alt.Scale(domain=["Winner", "Others"], range=[charts.ACCENT, "#C9D3CF"]),
                      x_title=x_title or x, tooltip=[y, x], text=x if fmt is None else None)
    return lambda: st.altair_chart(ch, width="stretch")


# ---------------------------------------------------------------- slide builders
def build_slides(rd, show_votes: bool, rounds_n: int) -> tuple[list, list]:
    """Returns (slides, skipped) where skipped = [(title, reason)] for awards without data or hidden by privacy."""
    sc = rd.scope
    slides, skipped = [], []
    t = 0

    def add(**kw):
        nonlocal t
        slides.append(Slide(theme=t, **kw)); t += 1

    label = rd.meta["label"]
    single = len(sc["leagues"]) == 1
    add(key="intro", kicker=label, title="Music League Wrapped",
        subtitle="This league in songs, votes and bragging rights." if single else "Your group's time in songs, votes and bragging rights.",
        chips=[("Leagues", len(sc["leagues"])), ("Rounds", rounds_n), ("Songs", f"{sc['submissions']:,}"), ("Votes", f"{sc['votes']:,}"), ("Players", sc["players"])])

    # 1 champion
    if rd.has("overall_champion"):
        d = rd.table("overall_champion"); w = _tops(d); r = w.iloc[0]
        add(key="overall_champion", kicker="Overall champion", title=_names(w["player"]),
            subtitle=f"{r.total_points:,.0f} points across {r.submissions:.0f} submissions" + (" (co-champions)" if len(w) > 1 else ""),
            chips=[("Points per submission", _fmt_num(r.avg_points_per_submission, 2)), ("Round wins", int(r.round_wins)), ("Podium finishes", int(r.podiums))],
            footer="Players who joined more rounds had more chances to score: compare points per submission too.",
            extra=_bar(d.sort_values("total_points", ascending=False), "player", "total_points", highlight=list(w["player"]), x_title="Total points"),
            notes=_notes(rd, "overall_champion"))
    else:
        skipped.append(("Overall Champion", "no data"))

    # 2 highest scoring song
    if rd.has("highest_scoring_song"):
        d = rd.table("highest_scoring_song"); w = _tops(d); r = w.iloc[0]
        bs = rd.table("highest_scoring_song", "by_share")
        cap = _cap_known(rd)
        share_txt = lambda v: f"{v:.0%}" if cap else f"{v:.2f}"
        share_lbl = "Share of available points" if cap else "Points per eligible voter"
        add(key="highest_scoring_song", kicker="Highest scoring song", title=_names(w["song"]),
            subtitle=f"{r.artist} · submitted by {r.submitter} · League {r.league}, Round {r['round']}: {r.round_name}",
            chips=[("Points", int(r.total_points)), ("Voters", f"{int(r.supporters)} of {int(r.elig)}"), (share_lbl, share_txt(r.share_of_available_points))],
            footer=("Best by share of available points: " + _names(_tops(bs)["song"]) + f" ({_names(_tops(bs)['submitter'])})") if len(bs) else "",
            extra=lambda d=d: st.dataframe(d.head(8)[["song", "artist", "submitter", "round_name", "total_points", "supporters"]].rename(
                columns={"song": "Song", "artist": "Artist", "submitter": "Submitter", "round_name": "Round", "total_points": "Points", "supporters": "Voters"}),
                hide_index=True, width="stretch"),
            notes=_notes(rd, "highest_scoring_song"))
    else:
        skipped.append(("Highest Scoring Song", "no data"))

    # 3 podium
    if rd.has("podium_throne"):
        d = rd.table("podium_throne"); w = _tops(d); r = w.iloc[0]
        def podium_chart(d=d, w=w):
            long = d.head(10).melt(id_vars=["player"], value_vars=["gold", "silver", "bronze"], var_name="medal", value_name="count")
            order = d.head(10)["player"].tolist()
            ch = alt.Chart(long).mark_bar().encode(
                y=alt.Y("player:N", sort=order, title=None), x=alt.X("count:Q", title="Podium finishes", stack="zero"),
                color=alt.Color("medal:N", scale=alt.Scale(domain=["gold", "silver", "bronze"], range=["#E0B100", "#A9B2B8", "#B87333"]), legend=alt.Legend(title=None, orient="bottom")),
                tooltip=["player", "medal", "count"]).properties(height=alt.Step(24))
            st.altair_chart(ch, width="stretch")
        add(key="podium_throne", kicker="Podium throne", title=_names(w["player"]),
            subtitle=f"{int(r.gold)} gold · {int(r.silver)} silver · {int(r.bronze)} bronze", chips=[("Weighted score", int(r.weighted_score)), ("Podiums", int(r.podiums)), ("Submissions", int(r.submissions))],
            footer="Gold = 3, silver = 2, bronze = 1. Tied songs share a place.", extra=podium_chart, notes=_notes(rd, "podium_throne"))
    else:
        skipped.append(("Podium Throne", "no data"))

    # 4 one-hit wonder
    if rd.has("one_hit_wonder"):
        d = rd.table("one_hit_wonder"); w = _tops(d); r = w.iloc[0]
        add(key="one_hit_wonder", kicker="One-hit wonder", title=_names(w["player"]),
            subtitle=f"“{r.best_song}” earned {r.best_points:.0f} points. Their other songs averaged {r.other_avg_points:.1f}.",
            chips=[("One-hit index", _fmt_num(r.one_hit_index, 2)), ("Round wins", int(r.round_wins)), ("Voters behind the hit", f"{r.best_supporters_pct:.0%}")],
            footer=f"{r.best_round}",
            extra=lambda d=d: st.dataframe(d.head(5)[["player", "best_song", "best_points", "other_avg_points", "one_hit_index"]].rename(
                columns={"player": "Player", "best_song": "Best song", "best_points": "Best points", "other_avg_points": "Others avg", "one_hit_index": "Index"}),
                hide_index=True, width="stretch", column_config={"Others avg": st.column_config.NumberColumn(format="%.1f"), "Index": st.column_config.NumberColumn(format="%.2f")}),
            notes=_notes(rd, "one_hit_wonder"))
    else:
        skipped.append(("One-Hit Wonder", "no eligible players"))

    # 5 consistency
    if rd.has("consistency"):
        d = rd.table("consistency"); w = _tops(d); r = w.iloc[0]
        add(key="consistency", kicker="Consistency", title=_names(w["player"]),
            subtitle=f"Average score {r.avg_normalized:.2f} with a spread of only {r.sd_normalized:.2f}.",
            chips=[("Consistency score", _fmt_num(r.consistency_score, 2)), ("Submissions counted", int(r.submissions_counted))],
            footer="Players with fewer submissions can top this one, so check the count.",
            extra=_bar(d, "player", "consistency_score", highlight=list(w["player"]), x_title="Consistency score"),
            notes=_notes(rd, "consistency"))
    else:
        skipped.append(("Consistency", "no eligible players"))

    # 6 blowout / squeaker
    if rd.has("blowout_squeaker"):
        bl = rd.table("blowout_squeaker"); sq = rd.table("blowout_squeaker", "squeaker_ranked"); tied = rd.table("blowout_squeaker", "tied_first_place_rounds")
        cap = _cap_known(rd)
        if len(bl):
            w = _tops(bl); r = w.iloc[0]; many = len(w) > 1
            add(key="blowout", kicker="The blowout", title=f"{len(w)} rounds tied for the biggest win" if many else _names(w["winning_song"]),
                subtitle=(" · ".join(f"{x.winning_song} ({x.submitter}, L{x.league} R{x.round})" for x in w.head(4).itertuples()) if many
                          else f"{r.submitter} won League {r.league} Round {r['round']} ({r.round_name}) by {r.margin:.0f} points."),
                chips=[("Winning margin", f"{r.margin:.0f} pts"), ("First vs second", f"{r.first_points:.0f} vs {r.second_points:.0f}"), ("Eligible voters", int(r.eligible_voters))],
                notes=_notes(rd, "blowout_squeaker"))
        if len(sq):
            w = _tops(sq); r = w.iloc[0]
            many = len(w) > 1
            add(key="squeaker", kicker="The closest call", title=f"{len(w)} rounds tied for the closest finish" if many else _names(w["winning_song"]),
                subtitle=(" · ".join(f"{x.winning_song} ({x.submitter}, L{x.league} R{x.round})" for x in w.head(4).itertuples()) if many
                          else f"{r.submitter} won League {r.league} Round {r['round']} ({r.round_name}) by just {r.margin:.0f} point."),
                chips=[("Winning margin", f"{r.margin:.0f} pt"), ("Rounds with a tied first place", len(tied))],
                footer="Tied first places are listed separately, with the official winner.")
    else:
        skipped.append(("Blowout vs. Squeaker", "no data"))

    # 7 vote spread
    if rd.has("vote_spread"):
        d = rd.table("vote_spread"); d = d[d["scope"] == "all"]
        if len(d):
            one = d[d["point_value"] == 1]["pct"].sum(); big = d[d["point_value"] >= 3]["votes"].sum(); mx = int(d["point_value"].max())
            add(key="vote_spread", kicker="How you voted", title=f"{one:.0%} of votes were a single point",
                subtitle=f"Only {int(big):,} of {int(d['votes'].sum()):,} votes gave 3 or more points. The biggest single vote was {mx}.",
                chips=[(f"{int(r.point_value)} pt" + ("s" if r.point_value > 1 else ""), f"{int(r.votes):,}") for r in d.itertuples()][:6],
                extra=lambda d=d: st.altair_chart(alt.Chart(d).mark_bar(cornerRadiusEnd=3, color=charts.ACCENT).encode(
                    x=alt.X("point_value:O", title="Points in one vote"), y=alt.Y("votes:Q", title="Votes"), tooltip=["point_value", "votes", alt.Tooltip("pct:Q", format=".1%")]).properties(height=260), width="stretch"),
                notes=_notes(rd, "vote_spread"))

    # 8 genre breakdown
    if rd.has("genre_breakdown"):
        d = rd.table("genre_breakdown"); top = d.iloc[0]
        best = d[d["submissions"] >= 5].sort_values("avg_normalized_score", ascending=False)
        def gchart(d=d):
            c1, c2 = st.columns(2)
            c1.markdown("**Share of submissions**")
            c1.altair_chart(charts.bar_h(d.head(10), "major_genre", "submission_share", tooltip=["major_genre", "submissions", alt.Tooltip("submission_share:Q", format=".1%")], x_title="Share").encode(
                x=alt.X("submission_share:Q", axis=alt.Axis(format="%"), title="Share")), width="stretch")
            dd = d[d["submissions"] >= 5].dropna(subset=["avg_normalized_score"])
            c2.markdown("**Average score (genres with 5+ songs)**")
            c2.altair_chart(charts.bar_h(dd, "major_genre", "avg_normalized_score", tooltip=["major_genre", "submissions", "avg_normalized_score", "genre_win_rate"], x_title="Average score"), width="stretch")
        add(key="genre_breakdown", kicker="The sound of the league", title=f"{top.major_genre} led the way",
            subtitle=f"{top.submission_share:.0%} of all submissions. " + (f"Best-scoring genre with 5+ songs: {best.iloc[0].major_genre}." if len(best) else ""),
            chips=[(r.major_genre, f"{r.submission_share:.0%}") for r in d.head(4).itertuples()], extra=gchart, notes=_notes(rd, "genre_breakdown"))

    # 9 you know who
    if rd.has("you_know_who"):
        d = rd.table("you_know_who"); w = _tops(d); r = w.iloc[0]
        add(key="you_know_who", kicker="You know who", title=_names(w["player"]),
            subtitle=f"{r.concentration:.0%} of their submissions were {r.top_genre}.", chips=[("Songs in that genre", f"{int(r.top_genre_count)} of {int(r.submissions)}")],
            extra=lambda d=d: st.dataframe(d.head(6)[["player", "top_genre", "top_genre_count", "submissions", "concentration"]].rename(
                columns={"player": "Player", "top_genre": "Top genre", "top_genre_count": "Songs", "submissions": "Submissions", "concentration": "Share"}),
                hide_index=True, width="stretch", column_config={"Share": st.column_config.NumberColumn(format="percent")}),
            notes=_notes(rd, "you_know_who"))
    else:
        skipped.append(("You Know Who", "no eligible players"))

    # 10 genre explorer
    if rd.has("genre_explorer"):
        d = rd.table("genre_explorer"); w = _tops(d); r = w.iloc[0]
        add(key="genre_explorer", kicker="Genre explorer", title=_names(w["player"]),
            subtitle=f"{int(r.distinct_major_genres)} different major genres across {int(r.submissions)} submissions.", chips=[("Evenness", _fmt_num(r.evenness, 2))],
            footer=str(r.genres) if len(w) == 1 else "", notes=_notes(rd, "genre_explorer"))
    else:
        skipped.append(("Genre Explorer", "no eligible players"))

    # 11 voting styles
    if rd.has("generosity"):
        eng = rd.table("generosity"); gl = rd.table("generosity", "guest_list_order"); ai = rd.table("generosity", "all_in_order")
        n = _notes(rd, "generosity")
        w = _tops(eng); r = w.iloc[0]
        add(key="generosity_engine", kicker="Generosity engine", title=_names(w["player"]),
            subtitle=f"Gave points to {r.avg_support_breadth:.0%} of the songs they could vote for.", chips=[("Songs supported per round", _fmt_num(r.avg_songs_supported, 1)), ("Ballots", int(r.ballots))], notes=n)
        w = _tops(gl); r = w.iloc[0]
        add(key="guest_list", kicker="Very exclusive guest list", title=_names(w["player"]),
            subtitle=f"The most selective voter: points went to just {r.avg_support_breadth:.0%} of the songs they could vote for.", chips=[("Songs supported per round", _fmt_num(r.avg_songs_supported, 1)), ("Ballots", int(r.ballots))], notes=n)
        w = _tops(ai); r = w.iloc[0]
        add(key="all_in", kicker="All-in voter", title=_names(w["player"]),
            subtitle=f"On average {r.avg_top_song_share:.0%} of a ballot's points went to a single favorite song.", chips=[("Ballots", int(r.ballots))], notes=n)
    else:
        skipped.append(("Generosity / Guest List / All-In", "no eligible players"))

    # 12-13 strong votes
    thr = (rd.awards.get("times_gave_3plus", {}).get("thresholds") or {}).get("points_at_least", 3)
    if rd.has("times_gave_3plus"):
        d = rd.table("times_gave_3plus"); bp = rd.table("times_gave_3plus", "by_rate"); w = _tops(d); r = w.iloc[0]; wr = _tops(bp).iloc[0]
        add(key="times_gave", kicker=f"{thr}+ point votes given", title=_names(w["player"]),
            subtitle=f"Handed out {int(r.high_votes_given)} votes of {thr} or more points. Highest rate: {wr.player} ({wr.high_vote_pct:.0%} of their votes).",
            chips=[("Strong votes", int(r.high_votes_given)), ("Different songs", int(r.unique_songs_high)), ("Different submitters", int(r.unique_submitters_high))],
            extra=_bar(d, "player", "high_votes_given", highlight=list(w["player"]), x_title=f"Votes of {thr}+ points"), notes=_notes(rd, "times_gave_3plus"))
    if rd.has("times_received_3plus"):
        d = rd.table("times_received_3plus"); bp = rd.table("times_received_3plus", "by_rate"); w = _tops(d); r = w.iloc[0]; wr = _tops(bp).iloc[0]
        add(key="times_received", kicker=f"{thr}+ point votes received", title=_names(w["player"]),
            subtitle=f"Songs earned {int(r.high_votes_received)} votes of {thr} or more points. Best per submission: {wr.player} ({wr.high_votes_per_submission:.2f}).",
            chips=[("Strong votes", int(r.high_votes_received)), ("Songs that got one", int(r.submissions_with_high_vote)), ("Different voters", int(r.unique_high_voters))],
            extra=_bar(d, "player", "high_votes_received", highlight=list(w["player"]), x_title=f"Votes of {thr}+ points received"), notes=_notes(rd, "times_received_3plus"))

    # 14 title cloud
    if rd.has("title_cloud"):
        allw = rd.table("title_cloud", "all_scopes"); allw = allw[allw["scope"] == "all"].head(40)
        th = rd.awards["title_cloud"].get("thresholds") or {}
        def cloud(allw=allw):
            mx = allw["count"].max() or 1
            cols = ["#0B5D3E", "#1F9D6B", "#3A1C71", "#B24592", "#1D4E89", "#E8683A"]
            spans = "".join(f"<span style='font-size:{14 + 40 * math.sqrt(r.count / mx):.0f}px;color:{cols[i % len(cols)]}'>{esc(r.word)}</span>" for i, r in enumerate(allw.itertuples()))
            st.markdown(f"<div class='cloud'>{spans}</div>", unsafe_allow_html=True)
        top = allw.iloc[0]
        add(key="title_cloud", kicker="Title cloud", title=f"“{top.word}” ruled the titles",
            subtitle=f"It appeared in {int(top['count'])} song titles. {th.get('unique_words', '')} different words were used in all.",
            chips=[(r.word, int(r.count)) for r in allw.head(5).itertuples()], extra=cloud, notes=_notes(rd, "title_cloud"))

    # 15 biggest fan (relationship data: respects the privacy switch)
    if rd.has("biggest_fan"):
        if show_votes:
            d = rd.table("biggest_fan")
            add(key="biggest_fan", kicker="Biggest fans", title="Everyone's biggest fan", subtitle="The voter who backed each person's songs the most, across the rounds they shared.",
                chips=[("Submitters with a fan", len(d)), ("Ties", int(d["tie"].sum()))],
                extra=lambda d=d: st.dataframe(d.assign(rate=d["support_rate"] * 100)[["submitter", "biggest_fan", "points_given", "shared_eligible_rounds", "rate", "favorite_submission"]].rename(
                    columns={"submitter": "Submitter", "biggest_fan": "Biggest fan", "points_given": "Points given", "shared_eligible_rounds": "Shared rounds", "rate": "Support rate", "favorite_submission": "Their favorite song"}),
                    hide_index=True, width="stretch", column_config={"Support rate": st.column_config.NumberColumn(format="%.0f%%")}),
                notes=_notes(rd, "biggest_fan"))
        else:
            skipped.append(("Biggest Fan", "hidden: 'Show who voted for whom' is off"))
    else:
        skipped.append(("Biggest Fan", "no data"))

    # outro: honest disclosure of the rules used
    ex = ", ".join(sc.get("performance_excluded_statuses", []))
    add(key="outro", kicker="Fine print", title="How these were worked out", subtitle="Everything comes from the tracker; nothing is estimated by hand.",
        chips=[("Leagues", ", ".join(str(x) for x in sc["leagues"]))],
        footer=f"Averages and consistency leave out songs marked: {ex}. " + ("" if _cap_known(rd) else "Scores are points per eligible voter (the maximum vote per song isn't recorded yet), so normalized awards are approximate. ")
        + "Ties are shown as co-winners.")
    return slides, skipped
