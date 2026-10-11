# Anime Production Growth — data science dashboard

A Django dashboard about the growth of anime: shows, manga and merchandise.
Fundamentals of Data Science course project.

## Run it (macOS)

Open Terminal and run these one at a time:

```
cd ~/Desktop/anime-growth-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

Then open http://127.0.0.1:8000 in a browser. Press Ctrl+C in Terminal to stop.

The SQLite database (`db.sqlite3`) is already built. To rebuild it from the CSV files:

```
python manage.py migrate
python manage.py load_data
```

## Pages

| Page | What it shows |
|---|---|
| Overview | Headline numbers, market forecast, titles per year, posters |
| Shows | Titles per year by format, seasons, genres, studios, scores (Matplotlib) |
| Manga | Launches per year, audiences, genres, most-followed titles |
| Merch & market | Revenue by segment, shares, market against output |
| Predictions | Three trend models per series, back-tested, projected to 2030 |
| Report | Findings, forecast table, figures, method, limits, PDF download |
| Data | Sources, CSV downloads, add a year (SQLite), JSON import, JSON API |

## Where each course concept is used

| Concept | File |
|---|---|
| pandas (grouping, crosstab, explode, shares) | `dashboard/analytics.py` |
| NumPy (design matrices, intervals, growth rates) | `dashboard/forecasting.py`, `dashboard/analytics.py` |
| Matplotlib (all static figures, PDF report) | `dashboard/charts.py` |
| scikit-learn (regression, MAPE, R²) | `dashboard/forecasting.py` |
| SQLite (tables, loading CSV, updates) | `dashboard/models.py`, `dashboard/management/commands/load_data.py` |
| JSON (API, import, export, source list) | `dashboard/views.py`, `dashboard/forms.py`, `data/sources.json` |
| Django (pages, forms, admin) | `dashboard/views.py`, `dashboard/templates/` |

## Data

All files are in `data/`. Details and links are in `data/sources.json`.

- `anime_titles.csv` — 39,571 titles from anime-offline-database (release 2026-27).
- `manga_titles.csv` — 43,982 titles from a 2022 MyAnimeList dump.
- `anime_market_segments.csv` — yearly revenue by segment, 2002–2024, from the
  Association of Japanese Animations (AJA) Anime Industry Reports. AJA publishes
  these as PDF charts, so the figures were typed into CSV by hand; each row's
  segments add up to the published total.
- `tv_anime_production_minutes.csv` — AJA, 2000–2020.

`scripts/build_datasets.py` is the script that turned the raw downloads into the first two CSVs.

## Things to know before presenting

- 2026 is not a full year in the anime data (collected July 2026), so analysis stops at 2025.
- Manga counts fall after 2016. Part of that is titles not yet catalogued in 2022,
  so the manga chart is a trend check to 2021 and has no 2030 forecast.
- Manga is counted in titles launched, not copies sold.
- Forecasts are trend lines. Merchandise and streaming have large back-test errors and are labelled low confidence.
- Poster images load from MyAnimeList when you are online. Offline, a coloured card with the title shows instead.

## Admin (optional)

```
python manage.py createsuperuser
```

Then visit http://127.0.0.1:8000/admin to edit any table.
