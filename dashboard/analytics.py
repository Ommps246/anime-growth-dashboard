"""All the pandas / NumPy analysis. Data is read from SQLite through the Django models."""
import re

import numpy as np
import pandas as pd

from .models import (AnimeTitle, MangaTitle, MarketRecord, ProductionMinutes,
                     SEGMENTS, SEGMENT_KEYS)

# The anime snapshot was taken in July 2026, so 2026 onward is only what has been
# announced so far. 2025 is the last complete year.
ANIME_START, ANIME_LAST_FULL = 1990, 2025
# The manga snapshot is from mid-2022. Counts peak in 2016 and fall afterwards; part
# of that fall is titles not yet catalogued, so 2016 is used as the last dependable year.
MANGA_START, MANGA_RELIABLE_END, MANGA_END = 1990, 2016, 2021

TYPE_ORDER = ["TV", "MOVIE", "OVA", "ONA", "SPECIAL"]
TYPE_LABEL = {"TV": "TV series", "MOVIE": "Films", "OVA": "OVA", "ONA": "Web (ONA)",
              "SPECIAL": "Specials"}
SEGMENT_LABEL = dict(SEGMENTS)

_cache = {}


def clear_cache():
    _cache.clear()


def cached(fn):
    def wrapper(*args):
        key = (fn.__name__,) + args
        if key not in _cache:
            _cache[key] = fn(*args)
        return _cache[key]
    wrapper.__name__ = fn.__name__
    return wrapper


# ---------------------------------------------------------------- data frames
@cached
def anime_df():
    cols = ["title", "type", "episodes", "status", "season", "year", "duration_min",
            "score", "origin", "studios", "genres", "source_material", "picture", "url"]
    return pd.DataFrame.from_records(AnimeTitle.objects.values(*cols), columns=cols)


@cached
def manga_df():
    cols = ["title", "type", "score", "scored_by", "status", "volumes", "chapters", "year",
            "members", "favorites", "genres", "demographics", "serializations", "picture", "url"]
    return pd.DataFrame.from_records(MangaTitle.objects.values(*cols), columns=cols)


@cached
def market_df():
    cols = ["year"] + SEGMENT_KEYS + ["total", "record_source"]
    df = pd.DataFrame.from_records(MarketRecord.objects.values(*cols), columns=cols)
    df[SEGMENT_KEYS + ["total"]] = df[SEGMENT_KEYS + ["total"]].astype(float)
    df = df.sort_values("year").reset_index(drop=True)
    df["domestic"] = df["total"] - df["overseas"]
    df["yoy_pct"] = df["total"].pct_change() * 100
    return df


@cached
def minutes_df():
    return pd.DataFrame.from_records(
        ProductionMinutes.objects.values("year", "minutes"), columns=["year", "minutes"])


def _origin(df, origin):
    return df if origin == "All" else df[df["origin"] == origin]


def cagr(first, last, years):
    """Compound annual growth rate in percent."""
    if not years or first <= 0:
        return float("nan")
    return ((last / first) ** (1 / years) - 1) * 100


# ---------------------------------------------------------------------- shows
@cached
def production_by_year(origin="Japan"):
    """Titles released per year, one column per format."""
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(ANIME_START, ANIME_LAST_FULL + 1) & df["type"].isin(TYPE_ORDER)]
    table = pd.crosstab(df["year"], df["type"]).reindex(columns=TYPE_ORDER, fill_value=0)
    table["TOTAL"] = table.sum(axis=1)
    return table


@cached
def episodes_by_year(origin="Japan"):
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(ANIME_START, ANIME_LAST_FULL) & (df["type"] == "TV")]
    return df.groupby("year")["episodes"].agg(["sum", "median", "count"])


@cached
def season_table(origin="Japan"):
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(2010, ANIME_LAST_FULL) & (df["type"] == "TV")
            & df["season"].isin(["WINTER", "SPRING", "SUMMER", "FALL"])]
    return pd.crosstab(df["year"], df["season"])[["WINTER", "SPRING", "SUMMER", "FALL"]]


def _studio_key(name):
    """'J.C.Staff Co., Ltd.' and 'j.c. staff' are the same studio."""
    n = re.sub(r"\b(co|ltd|inc|corp|corporation|company|k\.?k|llc)\b\.?", "", name.lower())
    return re.sub(r"[^a-z0-9]", "", n)


@cached
def top_studios(origin="Japan", since=2015, n=12):
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(since, ANIME_LAST_FULL) & (df["studios"] != "")
            & df["type"].isin(["TV", "MOVIE"])]
    s = df["studios"].str.split("|").explode().str.strip()
    s = s[s != ""].to_frame("name")
    s["key"] = s["name"].map(_studio_key)
    s = s[s["key"] != ""]
    # the dataset merges several sites, so one title can list a studio under two spellings
    per_title = s.reset_index().drop_duplicates(["index", "key"])
    counts = per_title["key"].value_counts().head(n)
    shortest = s.groupby("key")["name"].agg(lambda v: min(v, key=len))
    counts.index = [shortest[k] for k in counts.index]
    return counts


@cached
def genre_trend(origin="Japan", n=8):
    """Share of each year's tagged titles carrying a genre (a title can have several)."""
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(2000, ANIME_LAST_FULL) & (df["genres"] != "")]
    ex = df.assign(genre=df["genres"].str.split("|")).explode("genre")
    counts = ex.groupby(["year", "genre"]).size().unstack(fill_value=0)
    share = counts.div(df.groupby("year").size(), axis=0) * 100
    top = counts.loc[2016:].sum().sort_values(ascending=False).head(n).index
    return share[top]


@cached
def score_by_year(origin="Japan"):
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(2000, ANIME_LAST_FULL) & (df["type"] == "TV") & df["score"].notna()]
    g = df.groupby("year")["score"]
    return pd.DataFrame({"median": g.median(), "p25": g.quantile(.25), "p75": g.quantile(.75)})


@cached
def source_material_share(origin="Japan"):
    df = _origin(anime_df(), origin)
    df = df[df["year"].between(2005, ANIME_LAST_FULL) & (df["type"] == "TV")
            & (df["source_material"] != "Other / unknown")]
    t = pd.crosstab(df["year"], df["source_material"])
    return t.div(t.sum(axis=1), axis=0) * 100


@cached
def poster_wall(n=28):
    """Well-rated recent Japanese titles with a MyAnimeList poster, for the hero strip."""
    df = anime_df()
    df = df[(df["origin"] == "Japan") & df["year"].between(2012, ANIME_LAST_FULL)
            & (df["type"].isin(["TV", "MOVIE"])) & df["score"].notna()
            & df["picture"].str.contains("myanimelist", na=False)]
    df = df[(df["episodes"] >= 10) | (df["type"] == "MOVIE")]
    # one title per year first so the wall spans the whole period, then fill by score
    best = df.sort_values("score", ascending=False)
    per_year = best.groupby("year").head(2)
    rest = best.drop(per_year.index).head(max(0, n - len(per_year)))
    out = pd.concat([per_year, rest]).head(n).sample(frac=1, random_state=7)
    return out[["title", "year", "score", "picture", "url"]].to_dict("records")


@cached
def top_anime_of_year(year, n=6):
    df = anime_df()
    df = df[(df["origin"] == "Japan") & (df["year"] == year) & (df["type"] == "TV")
            & df["score"].notna() & (df["episodes"] >= 10)]
    return (df.sort_values("score", ascending=False).head(n)
            [["title", "year", "score", "picture", "url", "studios"]].to_dict("records"))


# ---------------------------------------------------------------------- manga
@cached
def manga_by_year():
    df = manga_df()
    df = df[df["year"].between(MANGA_START, MANGA_END)]
    label = {"manga": "Manga", "light_novel": "Light novels", "one_shot": "One-shots",
             "manhwa": "Manhwa", "manhua": "Manhua"}
    df = df[df["type"].isin(label)]
    t = pd.crosstab(df["year"], df["type"].map(label))[list(label.values())]
    t["TOTAL"] = t.sum(axis=1)
    return t


@cached
def manga_demographics():
    df = manga_df()
    df = df[df["year"].between(2000, MANGA_RELIABLE_END) & (df["demographics"] != "")
            & (df["type"] == "manga")]
    ex = df.assign(d=df["demographics"].str.split("|")).explode("d")
    t = ex.groupby(["year", "d"]).size().unstack(fill_value=0)
    keep = [c for c in ["Shounen", "Seinen", "Shoujo", "Josei", "Kids"] if c in t.columns]
    return t[keep]


@cached
def manga_genres(n=10):
    df = manga_df()
    df = df[df["year"].between(2000, MANGA_END) & (df["genres"] != "")]
    s = df["genres"].str.split("|").explode()
    return s.value_counts().head(n)


@cached
def manga_top(n=8):
    df = manga_df()
    df = df[df["type"].isin(["manga", "manhwa", "light_novel"])]
    return (df.sort_values("members", ascending=False).head(n)
            [["title", "year", "members", "score", "type", "picture", "url"]].to_dict("records"))


# --------------------------------------------------------------------- market
def market_shares():
    m = market_df()
    return m[SEGMENT_KEYS].div(m["total"], axis=0) * 100


def market_table():
    m = market_df()
    rows = []
    for r in m.to_dict("records"):
        r = {k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()}
        rows.append(r)
    return rows


# ----------------------------------------------------------------------- KPIs
@cached
def kpis():
    m = market_df()
    last, prev = m.iloc[-1], m.iloc[-2]
    prod = production_by_year("Japan")
    mg = manga_by_year()
    y0 = 2015
    k = {
        "market_year": int(last["year"]),
        "market_total_trn": last["total"] / 1000,
        "market_yoy": (last["total"] / prev["total"] - 1) * 100,
        "merch_bn": last["merchandising"],
        "merch_yoy": (last["merchandising"] / prev["merchandising"] - 1) * 100,
        "overseas_share": last["overseas"] / last["total"] * 100,
        "overseas_bn": last["overseas"],
        "streaming_bn": last["streaming"],
        "titles_year": ANIME_LAST_FULL,
        "titles": int(prod.loc[ANIME_LAST_FULL, "TOTAL"]),
        "tv_titles": int(prod.loc[ANIME_LAST_FULL, "TV"]),
        "titles_cagr": cagr(prod.loc[y0, "TOTAL"], prod.loc[ANIME_LAST_FULL, "TOTAL"],
                            ANIME_LAST_FULL - y0),
        "manga_year": MANGA_RELIABLE_END,
        "manga_titles": int(mg.loc[MANGA_RELIABLE_END, "TOTAL"]),
        "anime_rows": len(anime_df()),
        "manga_rows": len(manga_df()),
        "market_rows": len(m),
    }
    return k


@cached
def findings():
    """Plain-language findings for the report page, every number computed from the data."""
    m = market_df().set_index("year")
    y0, y1 = int(m.index.min()), int(m.index.max())
    prod = production_by_year("Japan")
    mg = manga_by_year()
    shares = market_shares().set_index(m.index)
    ten = y1 - 10
    cross = m[m["overseas"] > m["domestic"]].index.min()
    f = []
    f.append(("The market more than tripled",
              f"The anime industry market grew from ¥{m.loc[y0, 'total']/1000:.2f} trillion in {y0} "
              f"to ¥{m.loc[y1, 'total']/1000:.2f} trillion in {y1}, a compound growth rate of "
              f"{cagr(m.loc[y0, 'total'], m.loc[y1, 'total'], y1 - y0):.1f}% a year. Over the last "
              f"ten years ({ten}–{y1}) the rate was {cagr(m.loc[ten, 'total'], m.loc[y1, 'total'], 10):.1f}% a year."))
    f.append(("Overseas is now the biggest slice",
              f"Overseas revenue was {shares.loc[ten, 'overseas']:.0f}% of the market in {ten} and "
              f"{shares.loc[y1, 'overseas']:.0f}% in {y1}. It first passed the whole domestic market in "
              f"{int(cross)}."))
    f.append(("Merchandise is the largest domestic segment, but grows slowly",
              f"Merchandise brought in ¥{m.loc[y1, 'merchandising']:.0f} billion in {y1}, more than any "
              f"other domestic segment, yet it grew only "
              f"{cagr(m.loc[ten, 'merchandising'], m.loc[y1, 'merchandising'], 10):.1f}% a year over ten "
              f"years and its share fell from {shares.loc[ten, 'merchandising']:.0f}% to "
              f"{shares.loc[y1, 'merchandising']:.0f}%."))
    f.append(("Streaming replaced home video",
              f"Streaming rose from ¥{m.loc[ten, 'streaming']:.0f} billion to "
              f"¥{m.loc[y1, 'streaming']:.0f} billion between {ten} and {y1}, while home video fell "
              f"from ¥{m.loc[ten, 'video']:.0f} billion to ¥{m.loc[y1, 'video']:.0f} billion."))
    peak = int(prod.loc[:ANIME_LAST_FULL, "TOTAL"].idxmax())
    f.append((f"Output grew {prod.loc[ANIME_LAST_FULL, 'TOTAL'] / prod.loc[2000, 'TOTAL']:.1f}-fold since 2000, then levelled off",
              f"Japanese titles released per year went from {int(prod.loc[2000, 'TOTAL'])} in 2000 to "
              f"{int(prod.loc[ANIME_LAST_FULL, 'TOTAL'])} in {ANIME_LAST_FULL}. The peak so far was "
              f"{int(prod.loc[peak, 'TOTAL'])} titles in {peak}. TV series alone reached "
              f"{int(prod.loc[ANIME_LAST_FULL, 'TV'])} in {ANIME_LAST_FULL}, the highest complete year in the data."))
    yc = min(y1, ANIME_LAST_FULL)
    f.append(("Since 2015, money has grown faster than output",
              f"Between 2015 and {yc} the market grew {(m.loc[yc, 'total']/m.loc[2015, 'total']-1)*100:.0f}% "
              f"while the number of titles grew {(prod.loc[yc, 'TOTAL']/prod.loc[2015, 'TOTAL']-1)*100:.0f}%. "
              f"In the ten years before that it was the other way round: titles grew "
              f"{(prod.loc[2015, 'TOTAL']/prod.loc[2005, 'TOTAL']-1)*100:.0f}% and the market "
              f"{(m.loc[2015, 'total']/m.loc[2005, 'total']-1)*100:.0f}%."))
    f.append(("Manga launches climbed until 2016",
              f"Catalogued manga, light novel and manhwa launches rose from {int(mg.loc[2000, 'TOTAL'])} in 2000 "
              f"to {int(mg.loc[MANGA_RELIABLE_END, 'TOTAL'])} in {MANGA_RELIABLE_END}. Counts fall after that. "
              f"Part of the fall is titles not yet catalogued when the data was collected in 2022 and part may be "
              f"a real slowdown; this dataset cannot separate the two."))
    return f
