from django.db import models

SEGMENTS = [
    ("tv", "TV"),
    ("movie", "Movies"),
    ("video", "Home video"),
    ("streaming", "Streaming"),
    ("merchandising", "Merchandise"),
    ("music", "Music"),
    ("overseas", "Overseas"),
    ("pachinko", "Pachinko"),
    ("live_entertainment", "Live events"),
]
SEGMENT_KEYS = [k for k, _ in SEGMENTS]


class AnimeTitle(models.Model):
    title = models.CharField(max_length=400)
    type = models.CharField(max_length=12, db_index=True)
    episodes = models.IntegerField(default=0)
    status = models.CharField(max_length=12)
    season = models.CharField(max_length=10)
    year = models.IntegerField(db_index=True)
    duration_min = models.FloatField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    origin = models.CharField(max_length=8, db_index=True)
    studios = models.TextField(blank=True)
    genres = models.TextField(blank=True)
    source_material = models.CharField(max_length=20)
    picture = models.URLField(max_length=400, blank=True)
    url = models.URLField(max_length=400, blank=True)

    def __str__(self):
        return f"{self.title} ({self.year})"


class MangaTitle(models.Model):
    mal_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=400)
    type = models.CharField(max_length=14, db_index=True)
    score = models.FloatField(null=True, blank=True)
    scored_by = models.IntegerField(default=0)
    status = models.CharField(max_length=24)
    volumes = models.FloatField(null=True, blank=True)
    chapters = models.FloatField(null=True, blank=True)
    year = models.IntegerField(db_index=True)
    members = models.IntegerField(default=0)
    favorites = models.IntegerField(default=0)
    genres = models.TextField(blank=True)
    themes = models.TextField(blank=True)
    demographics = models.TextField(blank=True)
    serializations = models.TextField(blank=True)
    picture = models.URLField(max_length=400, blank=True)
    url = models.URLField(max_length=400, blank=True)

    def __str__(self):
        return f"{self.title} ({self.year})"


class MarketRecord(models.Model):
    """One year of the anime industry market, in billion yen (AJA, broad sense)."""

    year = models.IntegerField(unique=True)
    tv = models.FloatField(null=True, blank=True)
    movie = models.FloatField(null=True, blank=True)
    video = models.FloatField(null=True, blank=True)
    streaming = models.FloatField(null=True, blank=True)
    merchandising = models.FloatField(null=True, blank=True)
    music = models.FloatField(null=True, blank=True)
    overseas = models.FloatField(null=True, blank=True)
    pachinko = models.FloatField(null=True, blank=True)
    live_entertainment = models.FloatField(null=True, blank=True)
    total = models.FloatField()
    record_source = models.CharField(
        max_length=12, default="AJA report",
        help_text="'AJA report' for published figures, 'User entry' for rows added in the dashboard.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["year"]

    def segment_sum(self):
        return round(sum(getattr(self, k) or 0 for k in SEGMENT_KEYS), 1)

    def __str__(self):
        return f"{self.year}: ¥{self.total}bn"


class ProductionMinutes(models.Model):
    year = models.IntegerField(unique=True)
    minutes = models.IntegerField()

    class Meta:
        ordering = ["year"]
        verbose_name_plural = "production minutes"
