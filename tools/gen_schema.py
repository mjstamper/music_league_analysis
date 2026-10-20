"""Regenerate SCHEMA.md from a real output folder:  python tools/gen_schema.py out > SCHEMA.md"""
import json, os, sys
import pandas as pd

out = sys.argv[1] if len(sys.argv) > 1 else "out"
m = json.load(open(f"{out}/manifest.json"))
L = ["# Output schema", "", f"schema_version {m.get('schema_version')}. Generated from a real run. Every CSV has a header row; booleans are True/False; blanks are NaN.", "",
     "`manifest.json` is the entry point: files (with row counts), config used, validation, warnings, league summaries and `recap_scopes`.", ""]
desc = {"data": "Cleaned base tables (one row per song / vote / ballot / round). Join on league, round, song_idx.",
        "recap": "Year recap. `recap/index.json` lists scopes. Each scope folder (`all`, `league_N`, `period_<name>`, `custom`) has `awards.json` "
                 "(winners, headline, notes, thresholds, file list) and one CSV per award table. Folder `all` is shown; others have the same files."}
groups = {}
for f in m["files"]:
    groups.setdefault(f["path"].split("/")[0], []).append(f)
for g in sorted(groups, key=lambda x: (x != "data", x != "recap", x)):
    if g.startswith("league_") and g != "league_1":
        continue
    L += [f"## {'league_N (one folder per league; League 1 shown)' if g == 'league_1' else g}", "",
          desc.get(g, "Per-league analysis tables. `summary.json` has headline facts. Optional `profile_narratives.json` ({person: text}) is read by the dashboard."), "",
          "| File | Rows | Columns |", "|---|---|---|"]
    for f in groups[g]:
        if g == "recap" and not f["path"].startswith("recap/all/"):
            continue
        if f["path"].endswith(".json"):
            continue
        cols = list(pd.read_csv(os.path.join(out, f["path"]), nrows=0).columns)
        L.append(f"| `{f['path']}` | {f['rows']} | {', '.join(cols)} |")
    L.append("")
print("\n".join(L))
