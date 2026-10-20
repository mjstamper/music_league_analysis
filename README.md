# Music League analysis script

Computes every metric from the tracker workbook with code, so results are reproducible and testable.
Writes tidy CSV/JSON that a dashboard (Streamlit, in `dashboard/`) or an AI agent can read. No metric is calculated by a model.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv sync                              # analysis dependencies only
uv sync --group dashboard            # also install Streamlit dashboard deps
```

## Run

```bash
uv run python -m ml_analysis --workbook "Music_League_-_Song_Tracker_v2.1.xlsx" --out out
```

| Option | Meaning |
|---|---|
| `--mode all` (default) | Every league + the year recap |
| `--mode league --league 4` | One league only |
| `--mode recap [--leagues 1-7]` | Recap only. Default = one recap for all complete leagues, one per complete league, plus any named periods. `--leagues` writes a single `custom` scope instead |
| `--config config.json` | Override thresholds/weights (see `config.example.json`) |
| `--cap 1=5,4=5` | Max votes per song by league, when the Rounds tab leaves it blank |
| `--strict` | Exit code 1 if any validation check fails |

Exit codes: 0 ok, 1 validation failed (`--strict`), 2 data error (the message says what to fix).
A full run takes about 5 seconds. Tested with Python 3.12 and pandas 3.0.

## What it does

1. **Load and validate** (`data.py`): reads All Song Rankings, Votes, Rounds, Participants. Joins votes to songs on
   (League #, Round #, Spotify URI). Drops and reports self-votes, duplicates and zero/blank rows. Halts if any vote fails to join.
   Recomputes Place, Raw Points and Status independently and compares them with the workbook's formulas (all agree on the current file).
2. **League analysis** (`league.py`, per league): round results, leaderboard, song leaders, biggest fans + matrix,
   taste twins (cosine + Jaccard, near-tie and confidence flags), underrated gems (with 50/50 sensitivity), genre summaries,
   profile data (submissions, top votes, support shares, submitted-vs-rewarded mix), QC reconciliation.
3. **Recap** (`recap.py`): the 15 awards from the recap guidelines, each with winners, ranked table, ineligible list, thresholds and notes. One recap is written per scope under `out/recap/<scope>/`: `all` (every complete league), `league_N`, and any named period from `recap_periods` in the config, e.g. `{"Year One": [1,2,3,4,5,6,7]}` (leagues have no dates in the workbook, so a period is a list of leagues).
4. **Export** (`export.py`): `manifest.json`, `data/`, `league_N/`, `recap/`. See `SCHEMA.md`.

Genre/subgenre *research* and profile *narratives* are not in this script (they need web research and writing).
The script reads the workbook's Genre / Major Genre / Subgenre columns and reports subgenres only once that column is filled.

## Defaults you should confirm (all in `config.py`, all printed in `manifest.json`)

| Default | Why it matters | Effect observed on Leagues 1-7 |
|---|---|---|
| Recap performance measures exclude Forfeited, Zero-vote, Mismatch and Unscored songs | Forfeits are a penalty, not a performance | Only One-Hit Wonder changes if Zero-vote songs are kept: Collin -> Nicole |
| Max Votes per Song is blank on every round, so cap = 1 | Normalized scores are "points per eligible voter" and can exceed 1 | Fill the Rounds tab or pass `--cap` |
| A league is "complete" when every listed round is scored and it has 8+ rounds | League 8 lists only 2 rounds, so it must not count as complete early | League 8 is excluded from the recap |
| Twins need 4+ shared rounds; near-tie margin 0.03 | Keeps weak matches from being reported as twins | See `league_N/twins.csv` |
| Ties are never broken silently | Co-winners are reported with `status = co-winners` | Squeaker is a 3-way tie |

## Tests

```bash
uv run python -m unittest discover -s tests -v
# also run the real-workbook checks (bash):
ML_WORKBOOK="Music_League_-_Song_Tracker_v2.1.xlsx" uv run python -m unittest discover -s tests -v
# PowerShell:
$env:ML_WORKBOOK="Music_League_-_Song_Tracker_v2.1.xlsx"; uv run python -m unittest discover -s tests -v
```
17 tests: math helpers, tie handling, a hand-checkable synthetic league (statuses, places, fans, twin score, forfeits),
failure modes (unjoined votes, self-votes, duplicates, mismatches), tiny-data robustness, CLI, and known numbers from the real workbook.

## Privacy

`data/votes.csv` and the fan/twin files show who voted for whom. Participants' export usernames are deliberately not exported.
Decide who may see these before sharing the dashboard.

## Dashboard

The dashboard (league view and the Wrapped-style recap) lives in `dashboard/` (see its README). Contract notes for any other consumer:

Read `out/manifest.json` first (leagues, warnings, award headlines, file list), then load CSVs. Suggested Streamlit structure:
sidebar league picker (`leagues_analyzed`), tabs for Standings, Songs, Fans, Twins, Gems, Genres, Profiles, Recap.
Use `@st.cache_data` keyed on `manifest.json`'s `run_utc`. Show `warnings` at the top of every page.
