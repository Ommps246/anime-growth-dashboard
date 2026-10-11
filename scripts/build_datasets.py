"""
Turn the raw online downloads into the tidy CSV files used by the dashboard.

Usage:
    python scripts/build_datasets.py <folder-with-raw-downloads> <output-data-folder>

Raw downloads expected in the first folder:
    aod.json        anime-offline-database (manami-project, GitHub releases)
    manga_raw.csv   MyAnimeList manga dump (lengoctuong/Prj-Manga-Dataset_Programming4DS)

The two small AJA tables (market segments, TV production minutes) were typed in
from the Association of Japanese Animations "Anime Industry Report" summaries
and already live in the data folder, so this script only validates them.
"""
import ast
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GENRES = [
    "action", "adventure", "comedy", "drama", "fantasy", "horror", "mystery",
    "romance", "sci-fi", "slice of life", "sports", "supernatural", "mecha",
    "music", "kids", "isekai", "school", "historical", "thriller", "psychological",
]


def build_anime(raw: Path, out: Path) -> pd.DataFrame:
    data = json.load(open(raw / "aod.json", encoding="utf-8"))["data"]
    rows = []
    for a in data:
        tags = set(a.get("tags") or [])
        if "chinese animation" in tags or "chinese production" in tags:
            origin = "China"
        elif "korean animation" in tags:
            origin = "Korea"
        else:
            origin = "Japan"
        mal = next((s for s in a["sources"] if "myanimelist.net" in s), "")
        dur = (a.get("duration") or {}).get("value")
        rows.append({
            "title": a["title"],
            "type": a["type"],
            "episodes": a.get("episodes") or 0,
            "status": a["status"],
            "season": (a.get("animeSeason") or {}).get("season") or "UNDEFINED",
            "year": (a.get("animeSeason") or {}).get("year"),
            "duration_min": round(dur / 60, 1) if dur else np.nan,
            "score": round((a.get("score") or {}).get("arithmeticMean", np.nan), 2),
            "origin": origin,
            "studios": "|".join(a.get("studios") or []),
            "genres": "|".join(g for g in GENRES if g in tags),
            "source_material": (
                "Manga" if "based on a manga" in tags or "manga" in tags else
                "Light novel" if "based on a light novel" in tags or "light novel" in tags else
                "Game" if "based on a video game" in tags or "based on a game" in tags else
                "Original" if "original work" in tags else "Other / unknown"
            ),
            "picture": a.get("picture") or "",
            "url": mal or (a["sources"][0] if a["sources"] else ""),
        })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df = df[df["year"].between(1960, 2027)]
    df = df.sort_values(["year", "title"]).reset_index(drop=True)
    df.to_csv(out / "anime_titles.csv", index=False)
    return df


def _join(cell) -> str:
    try:
        v = ast.literal_eval(cell) if isinstance(cell, str) else []
    except (ValueError, SyntaxError):
        v = []
    return "|".join(str(x) for x in v)


def build_manga(raw: Path, out: Path) -> pd.DataFrame:
    cols = ["manga_id", "title", "type", "score", "scored_by", "status", "volumes",
            "chapters", "start_date", "end_date", "members", "favorites", "sfw",
            "genres", "themes", "demographics", "serializations", "main_picture", "url"]
    df = pd.read_csv(raw / "manga_raw.csv", usecols=cols, low_memory=False)
    df = df[df["sfw"].astype(str) == "True"].drop(columns="sfw")
    for c in ["genres", "themes", "demographics", "serializations"]:
        df[c] = df[c].map(_join)
    df["year"] = pd.to_datetime(df["start_date"], errors="coerce").dt.year
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df = df[df["year"].between(1960, 2023)]
    df = df.rename(columns={"main_picture": "picture"})
    df = df.sort_values(["year", "title"]).reset_index(drop=True)
    df.to_csv(out / "manga_titles.csv", index=False)
    return df


def check_market(out: Path) -> pd.DataFrame:
    m = pd.read_csv(out / "anime_market_segments.csv")
    seg = ["tv", "movie", "video", "streaming", "merchandising", "music",
           "overseas", "pachinko", "live_entertainment"]
    diff = (m[seg].fillna(0).sum(axis=1) - m["total"]).abs()
    bad = m.loc[diff > 1.0, "year"].tolist()
    print("market rows:", len(m), "| years where segments != total:", bad or "none")
    return m


if __name__ == "__main__":
    raw, out = Path(sys.argv[1]), Path(sys.argv[2])
    a = build_anime(raw, out)
    print("anime:", a.shape, a["year"].min(), a["year"].max())
    mg = build_manga(raw, out)
    print("manga:", mg.shape, mg["year"].min(), mg["year"].max())
    check_market(out)
