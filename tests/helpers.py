"""Build a tiny synthetic tracker workbook with hand-checkable answers."""
import os
import pandas as pd

LEAGUE = "Test League (1st League)"


def songs_rows():
    # (song, artist, genre, submitter, round, points, n_voters, uri)
    r1, r2 = "1 - Alpha", "2 - Beta"
    return [
        ("sA", "Art A", "Pop", "A", r1, 3, 2, "u:A1"), ("sB", "Art B", "Rock", "B", r1, 2, 1, "u:B1"),
        ("sC", "Art C", "Pop", "C", r1, 1, 1, "u:C1"), ("sD", "Art D", "Rock", "D", r1, 0, 2, "u:D1"),   # D did not vote: forfeited
        ("sA2", "Art A", "Pop", "A", r2, 4, 3, "u:A2"), ("sB2", "Art B", "Rock", "B", r2, 3, 2, "u:B2"),
        ("sC2", "Art C", "Pop", "C", r2, 3, 2, "u:C2"), ("sD2", "Art D", "Rock", "D", r2, 2, 1, "u:D2"),
        ("sE2", "Art E", "Jazz/Vocal", "E", r2, 0, 0, "u:E2"),                                              # nobody voted: zero-vote
    ]


def votes_rows():
    # (round, voter, uri, points)
    return [(1, "A", "u:B1", 2), (1, "A", "u:C1", 1), (1, "B", "u:A1", 2), (1, "B", "u:D1", 1), (1, "C", "u:A1", 1), (1, "C", "u:D1", 2),
            (2, "A", "u:B2", 1), (2, "A", "u:C2", 2), (2, "B", "u:A2", 2), (2, "B", "u:C2", 1), (2, "C", "u:A2", 1), (2, "C", "u:D2", 2),
            (2, "D", "u:A2", 1), (2, "D", "u:B2", 2)]


def write_workbook(path, songs=None, votes=None):
    songs = songs or songs_rows()
    votes = votes or votes_rows()
    s = pd.DataFrame(songs, columns=["Song", "Artist", "Genre", "Submitter", "Round", "Points", "# of Voters", "Spotify URI"])
    s["League"] = LEAGUE
    s["League #"] = 1
    s["Round #"] = s["Round"].str.extract(r"^(\d+)")[0].astype(int)
    s["Major Genre"] = s["Genre"]
    v = pd.DataFrame(votes, columns=["Round #", "Voter", "Spotify URI", "Points"])
    v.insert(0, "League #", 1)
    r = pd.DataFrame({"League #": [1, 1], "League": LEAGUE, "Round #": [1, 2], "Round Name": ["Alpha", "Beta"]})
    p = pd.DataFrame({"Name": ["A", "B", "C", "D", "E"]})
    with pd.ExcelWriter(path) as xw:
        s.to_excel(xw, sheet_name="All Song Rankings", index=False)
        v.to_excel(xw, sheet_name="Votes", index=False)
        r.to_excel(xw, sheet_name="Rounds", index=False)
        p.to_excel(xw, sheet_name="Participants", index=False)
    return path
