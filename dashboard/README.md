# Music League dashboard (league view)

Streamlit app that reads the output folder written by `ml_analysis` (see `../SCHEMA.md`). It never reads the workbook,
so the analysis script is the single place where numbers are calculated.

## Run

From the project root (install dashboard deps with `uv sync --group dashboard` first):

```bash
uv run python -m ml_analysis --workbook Music_League_-_Song_Tracker_v2.1.xlsx --out out
cd dashboard
uv run streamlit run app.py
```

Set `ML_OUT` to the analysis output folder if it is not `../out` (bash: `ML_OUT=../out`; PowerShell: `$env:ML_OUT="../out"`).

The app has two pages (sidebar navigation): **League view** and **Recap (Wrapped)**. In League view, pick a league in the sidebar (defaults to the latest scored league). "Reload data" re-reads the files after you re-run the analysis.

## League view tabs

| Tab | What it shows |
|---|---|
| Overview | KPIs, standings (official points with points lost to forfeits), round winners, round explorer |
| Songs | Top 5 by total and by average per eligible voter, filterable song table, broad-vs-strong-appeal chart |
| Fans | Biggest fan per submitter, voter-to-submitter heatmap, drill-down |
| Taste twins | Twin per voter with confidence and near-tie flags, pair heatmap, drill-down, how it is calculated |
| Underrated gems | Top gems, where they sit, 50/50 sensitivity, forfeited songs excluded |
| Genres | Major genre / genre label / subgenre (when filled): counts, top 5, average points |
| Profiles | Per person: KPIs, submissions, submitted-vs-rewarded genre mix, rewarded songs, most supported |
| Data checks | Validation results, league reconciliation, settings used, CSV downloads |

Leagues with no votes yet (for example League 8) show standings, songs and genres, and explain what is unavailable.

## Recap (Wrapped)

For the whole group, live in the app. Pick the scope in the sidebar: all complete leagues, a single league, or a named period
(add periods with `recap_periods` in the analysis config; leagues have no dates in the workbook, so a period is a list of leagues).

- **Story** steps through full-width cards (Back / Next / Jump to): champion, highest scoring song, podium, one-hit wonder, consistency,
  blowout and closest call, vote spread, genre mix, genre concentration and range, three voting styles, strong votes given and received,
  title cloud, biggest fans, and a fine-print card that states the rules used (excluded song types, approximate scores, ties).
- **All awards** shows every card at once.
- Each card has a "How this is calculated" panel with the thresholds used.
- Ties are shown as co-winners. Awards with no eligible players are listed under "Awards not shown".
- The Biggest fans card reveals who backed whom, so it follows the privacy switch below.
- Voting-style cards use friendly framing: "Very Exclusive Guest List" is described as the most selective voter. Review award names before sharing with the group.

## Privacy

The sidebar switch **Show who voted for whom** hides the Fans and Twins tabs and the voting parts of Profiles.
Set `ML_SHOW_VOTES=0` to start with it off for a shared deployment. Note that the CSVs in the output folder still contain
voter names: protect the folder itself, not only the screen.

## Written profiles

Profiles show a paragraph when `league_N/profile_narratives.json` exists, as `{"Person": "text"}`.
This is where the agent's narrative output plugs in; nothing in the dashboard generates text.

## Tests

From `dashboard/` (after `uv sync --group dashboard` at the project root):

```bash
uv run python -m unittest discover -s tests -v
# optional real-data check: ML_OUT=../out (bash) or $env:ML_OUT="../out" (PowerShell)
```
Uses Streamlit's headless `AppTest`: renders every league, steps through every recap slide of every scope, gallery mode, the missing-folder error, and the privacy switch.
Tested with Streamlit 1.66, Altair 6.3, pandas 3.0.

## Next

Per-player cards (each person's own recap), export to images or PDF, and dates on leagues so periods can be real calendar ranges.
