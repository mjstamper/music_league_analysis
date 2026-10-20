"""Command line entry point:  python -m ml_analysis --workbook tracker.xlsx --out out"""
from __future__ import annotations
import argparse
import re
import sys

from .config import Config
from .data import DataError, load_dataset
from .export import write_all
from .league import analyze_league
from .recap import build_recap


def _parse_leagues(text: str) -> list:
    out = []
    for part in text.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return sorted(set(out))


def _fmt(leagues: list) -> str:
    ls = sorted(leagues)
    if len(ls) > 1 and ls == list(range(ls[0], ls[-1] + 1)):
        return f"{ls[0]}-{ls[-1]}"
    return ", ".join(str(x) for x in ls)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "period"


def _title(label: str) -> str:
    return re.sub(r"\s*\(\d+(?:st|nd|rd|th) League\)\s*$", "", str(label))


def recap_scopes(ds, cfg, leagues_arg, complete) -> list:
    """[(key, label, leagues)]: all complete leagues, each complete league, named periods; or one custom scope."""
    if leagues_arg:
        ls = _parse_leagues(leagues_arg)
        return [("custom", f"Leagues {_fmt(ls)}", ls)]
    if not complete:
        raise DataError("No complete leagues found for the recap. Use --leagues to choose some.")
    titles = ds.songs.groupby("league")["league_label"].first().to_dict()
    scopes = [("all", f"All complete leagues ({_fmt(complete)})", complete)]
    scopes += [(f"league_{n}", f"League {n}: {_title(titles[n])}", [n]) for n in complete]
    for label, ls in cfg.recap_periods.items():
        bad = [n for n in ls if n not in ds.leagues()]
        if bad:
            raise DataError(f"recap_periods['{label}'] lists leagues not in the workbook: {bad}")
        scopes.append((f"period_{_slug(label)}", f"{label} (Leagues {_fmt(ls)})", sorted(ls)))
    return scopes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ml_analysis", description="Music League analysis: league metrics and year recap awards.")
    ap.add_argument("--workbook", required=True, help="Path to the tracker workbook (v2.1 structure)")
    ap.add_argument("--out", default="out", help="Output folder (default: out)")
    ap.add_argument("--mode", choices=["all", "league", "recap"], default="all")
    ap.add_argument("--league", type=int, help="League number for --mode league")
    ap.add_argument("--leagues", help="Leagues for the recap, e.g. 1-7 (default: every complete league)")
    ap.add_argument("--config", help="JSON file overriding thresholds and defaults")
    ap.add_argument("--cap", help="Max votes per song by league when the Rounds tab is blank, e.g. '1=5,4=5'")
    ap.add_argument("--strict", action="store_true", help="Exit with code 1 if any validation check fails")
    a = ap.parse_args(argv)
    try:
        cfg = Config.from_json(a.config)
        if a.cap:
            cfg.cap_overrides = {int(k): float(v) for k, v in (p.split("=") for p in a.cap.split(","))}
        ds = load_dataset(a.workbook, cfg)
        league_results, recaps = {}, {}
        if a.mode in ("all", "league"):
            if a.mode == "league" and not a.league:
                ap.error("--league is required with --mode league")
            for n in ([a.league] if a.league else ds.leagues()):
                league_results[n] = analyze_league(ds, n, cfg)
        if a.mode in ("all", "recap"):
            complete = sorted(int(x) for x in ds.rounds[ds.rounds["league_complete"].fillna(False)]["league"].unique())
            for key, label, ls in recap_scopes(ds, cfg, a.leagues, complete):
                recaps[key] = dict(label=label, leagues=ls, result=build_recap(ds, ls, cfg))
        m = write_all(ds, cfg, a.out, league_results, recaps)
    except DataError as e:
        print(f"DATA ERROR: {e}", file=sys.stderr)
        return 2
    v = m["validation"]
    print(f"Done. Validation: {v['pass_']} pass, {v['fail']} fail. Leagues analyzed: {m['leagues_analyzed']}. Recap scopes: {[x['key'] for x in m['recap_scopes']]}.")
    for w in m["warnings"]:
        print("  note:", w)
    for f in v["failures"]:
        print("  FAIL:", f)
    print(f"Output: {a.out}/manifest.json ({len(m['files'])} files)")
    return 1 if (a.strict and v["fail"]) else 0


if __name__ == "__main__":
    sys.exit(main())
