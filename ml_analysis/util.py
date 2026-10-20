"""Small, well-tested helpers: text normalisation, ranking, ties, similarity."""
from __future__ import annotations
import math
import re
import unicodedata
import numpy as np
import pandas as pd


def nk(text) -> str:
    """Lowercase, strip accents, drop everything except a-z0-9 (matches the workbook's Key columns)."""
    s = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def competition_places(points, voters) -> np.ndarray:
    """Music League placing: more points first, then more voters; ties share a place; next place skips."""
    p = np.asarray(points, dtype=float)
    v = np.asarray(voters, dtype=float)
    out = np.empty(len(p), dtype=int)
    for i in range(len(p)):
        out[i] = 1 + int(np.sum(p > p[i])) + int(np.sum((p == p[i]) & (v > v[i])))
    return out


def safe_div(a, b):
    try:
        if b is None or b == 0 or (isinstance(b, float) and math.isnan(b)):
            return float("nan")
        return a / b
    except TypeError:
        return float("nan")


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    pa, pb = a > 0, b > 0
    union = int(np.sum(pa | pb))
    if union == 0:
        return float("nan")
    return float(np.sum(pa & pb)) / union


def pielou(counts) -> float:
    """Evenness H / ln(k). 0 when only one category, NaN when none."""
    c = np.asarray([x for x in counts if x > 0], dtype=float)
    if len(c) == 0:
        return float("nan")
    if len(c) == 1:
        return 0.0
    p = c / c.sum()
    return float(-(p * np.log(p)).sum() / math.log(len(c)))


def rank_and_winners(df: pd.DataFrame, keys: list[tuple[str, bool]], tol: float = 1e-9):
    """Sort by (column, ascending) keys. Winners = every row tied with the top row on ALL keys.

    Returns (sorted_df_with_rank, winners_df, status) where status is 'winner', 'co-winners' or 'none'.
    Never breaks a tie silently: unresolved ties come back as co-winners.
    """
    if df is None or len(df) == 0:
        return df, df, "none"
    cols = [k for k, _ in keys]
    d = df.sort_values(cols, ascending=[a for _, a in keys], kind="mergesort").reset_index(drop=True)
    top = d.iloc[0]
    mask = np.ones(len(d), dtype=bool)
    for k, _ in keys:
        a, b = d[k].to_numpy(), top[k]
        if pd.api.types.is_numeric_dtype(d[k]):
            mask &= np.isclose(a.astype(float), float(b), atol=tol, rtol=0, equal_nan=True)
        else:
            mask &= (a == b)
    # dense-ish rank: rows tied with the row above on all keys share its rank
    ranks, r = [], 0
    for i in range(len(d)):
        if i == 0:
            r = 1
        else:
            same = True
            for k, _ in keys:
                x, y = d.at[i, k], d.at[i - 1, k]
                if pd.api.types.is_numeric_dtype(d[k]):
                    same &= bool(np.isclose(float(x), float(y), atol=tol, rtol=0, equal_nan=True))
                else:
                    same &= (x == y)
            if not same:
                r = i + 1
        ranks.append(r)
    d.insert(0, "rank", ranks)
    winners = d[mask]
    return d, winners, ("winner" if len(winners) == 1 else "co-winners")


def title_words(title: str) -> list[str]:
    """Words from a song title: lowercase, drop (feat. ...) / [..] / '- Remastered' style suffixes, punctuation."""
    t = str(title).lower()
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", t)
    t = re.sub(r"\s-\s(?:.*?(?:remaster|remix|version|edit|mix|mono|stereo|live|from|soundtrack|cast|recording)).*$", " ", t)
    t = t.replace("\u2019", "'")
    t = re.sub(r"[^a-z0-9' ]", " ", t)
    words = [w.strip("'") for w in t.split()]
    return [w.replace("'", "") for w in words if w.strip("'")]
