"""Load the CSV files in data/ into the SQLite database.

    python manage.py load_data            # everything
    python manage.py load_data --market   # only the market + minutes tables
"""
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard import analytics
from dashboard.models import (AnimeTitle, MangaTitle, MarketRecord,
                              ProductionMinutes, SEGMENT_KEYS)


def _clean(df):
    """NaN -> None so SQLite stores NULL instead of the string 'nan'."""
    return df.astype(object).where(pd.notna(df), None)


def load_market():
    df = _clean(pd.read_csv(settings.DATA_DIR / "anime_market_segments.csv"))
    with transaction.atomic():
        MarketRecord.objects.all().delete()
        MarketRecord.objects.bulk_create([
            MarketRecord(year=int(r["year"]), total=r["total"], record_source="AJA report",
                         **{k: r[k] for k in SEGMENT_KEYS})
            for r in df.to_dict("records")
        ])
        mins = pd.read_csv(settings.DATA_DIR / "tv_anime_production_minutes.csv")
        ProductionMinutes.objects.all().delete()
        ProductionMinutes.objects.bulk_create(
            [ProductionMinutes(year=int(y), minutes=int(m)) for y, m in mins.values])
    analytics.clear_cache()
    return len(df)


class Command(BaseCommand):
    help = "Load the CSV datasets into SQLite"

    def add_arguments(self, parser):
        parser.add_argument("--market", action="store_true", help="only reload market tables")

    def handle(self, *args, **opts):
        self.stdout.write(f"market rows: {load_market()}")
        if opts["market"]:
            return

        a = pd.read_csv(settings.DATA_DIR / "anime_titles.csv")
        for c in ["studios", "genres", "picture", "url"]:
            a[c] = a[c].fillna("")
        a = _clean(a)
        with transaction.atomic():
            AnimeTitle.objects.all().delete()
            AnimeTitle.objects.bulk_create(
                [AnimeTitle(**r) for r in a.to_dict("records")], batch_size=2000)
        self.stdout.write(f"anime rows: {len(a)}")

        m = pd.read_csv(settings.DATA_DIR / "manga_titles.csv")
        m = m.rename(columns={"manga_id": "mal_id"}).drop(columns=["start_date", "end_date"])
        for c in ["genres", "themes", "demographics", "serializations", "picture", "url"]:
            m[c] = m[c].fillna("")
        for c in ["scored_by", "members", "favorites"]:
            m[c] = m[c].fillna(0).astype(int)
        m = _clean(m.replace({np.inf: None}))
        with transaction.atomic():
            MangaTitle.objects.all().delete()
            MangaTitle.objects.bulk_create(
                [MangaTitle(**r) for r in m.to_dict("records")], batch_size=2000)
        self.stdout.write(f"manga rows: {len(m)}")
        analytics.clear_cache()
        self.stdout.write(self.style.SUCCESS("SQLite database is ready."))
