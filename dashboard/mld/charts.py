"""Altair chart helpers with one consistent look."""
from __future__ import annotations
import altair as alt
import numpy as np
import pandas as pd

ACCENT = "#1F9D6B"
STATUS_COLORS = {"OK": "#1F9D6B", "Forfeited": "#9AA5A1", "Zero-vote": "#E0A526", "Mismatch": "#D1495B", "Unscored": "#CBD5D1"}
STATUS_DOMAIN = list(STATUS_COLORS)
STATUS_RANGE = list(STATUS_COLORS.values())
SEQ = ["#EAF6F0", "#9FD8BC", "#1F9D6B", "#0B5D3E"]


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    return df.replace({np.nan: None})


def bar_h(df, y, x, *, color=None, color_scale=None, tooltip=None, height=None, x_title=None, sort="-x", text=None):
    d = _clean(df)
    h = height or alt.Step(24)
    if sort in ("-x", "x") and len(d):
        agg = d.groupby(y)[x].sum()
        sort = agg.sort_values(ascending=(sort == "x")).index.tolist()
    enc = dict(y=alt.Y(f"{y}:N", sort=sort, title=None, axis=alt.Axis(labelLimit=260, labelOverlap=False)),
               x=alt.X(f"{x}:Q", title=x_title or x))
    if color:
        enc["color"] = alt.Color(f"{color}:N", scale=color_scale, legend=alt.Legend(title=None, orient="bottom"))
    else:
        enc["color"] = alt.value(ACCENT)
    if tooltip:
        enc["tooltip"] = tooltip
    base = alt.Chart(d).mark_bar(cornerRadiusEnd=3).encode(**enc)
    if text:
        lab = alt.Chart(d).mark_text(align="left", dx=3, fontSize=11).encode(
            y=alt.Y(f"{y}:N", sort=sort), x=alt.X(f"{x}:Q"), text=alt.Text(f"{text}:Q", format=".0f"))
        base = base + lab
    return base.properties(height=h)


def heatmap(df, x, y, value, *, tooltip=None, height=None, label_format=".0f", scheme_range=SEQ, x_sort=None, y_sort=None,
            title=None, null_color="#EEF1F0", text=True):
    d = _clean(df)
    nx, ny = d[x].nunique(), d[y].nunique()
    h = height or max(220, 26 * ny + 70)
    base = alt.Chart(d).encode(
        x=alt.X(f"{x}:N", sort=x_sort, title=None, axis=alt.Axis(labelAngle=-40)),
        y=alt.Y(f"{y}:N", sort=y_sort, title=None))
    rect = base.mark_rect(stroke="white").encode(
        color=alt.condition(f"isValid(datum['{value}'])", alt.Color(f"{value}:Q", scale=alt.Scale(range=scheme_range), legend=alt.Legend(title=title or value)),
                            alt.value(null_color)),
        tooltip=tooltip)
    if not text:
        return rect.properties(height=h)
    mx = float(np.nanmax(d[value].astype(float))) if len(d) and d[value].notna().any() else 1.0
    lab = base.mark_text(fontSize=10).encode(
        text=alt.Text(f"{value}:Q", format=label_format),
        color=alt.condition(f"datum['{value}'] > {mx * 0.55}", alt.value("white"), alt.value("#1B2B27"))
    ).transform_filter(f"isValid(datum['{value}'])")
    return (rect + lab).properties(height=h)


def scatter(df, x, y, *, size=None, color=None, color_scale=None, tooltip=None, height=380, x_title=None, y_title=None, opacity=0.75):
    d = _clean(df)
    enc = dict(x=alt.X(f"{x}:Q", title=x_title or x), y=alt.Y(f"{y}:Q", title=y_title or y), tooltip=tooltip)
    if size:
        enc["size"] = alt.Size(f"{size}:Q", legend=None, scale=alt.Scale(range=[40, 500]))
    if color:
        enc["color"] = alt.Color(f"{color}:N", scale=color_scale, legend=alt.Legend(title=None))
    else:
        enc["color"] = alt.value(ACCENT)
    return alt.Chart(d).mark_circle(opacity=opacity, stroke="white").encode(**enc).properties(height=height)


def grouped_bar(df, category, value, series, *, height=None, value_title="Share", fmt="%"):
    d = _clean(df)
    n = d[category].nunique() if len(d) else 1
    return alt.Chart(d).mark_bar(cornerRadiusEnd=2).encode(
        y=alt.Y(f"{category}:N", sort="-x", title=None),
        x=alt.X(f"{value}:Q", title=value_title, axis=alt.Axis(format=".0%")),
        yOffset=alt.YOffset(f"{series}:N"),
        color=alt.Color(f"{series}:N", scale=alt.Scale(range=[ACCENT, "#F2A541"]), legend=alt.Legend(title=None, orient="bottom")),
        tooltip=[category, series, alt.Tooltip(f"{value}:Q", format=".1%")],
    ).properties(height=height or max(200, 38 * n + 40))
