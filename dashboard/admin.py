from django.contrib import admin

from .models import AnimeTitle, MangaTitle, MarketRecord, ProductionMinutes


@admin.register(AnimeTitle)
class AnimeAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "year", "season", "origin", "score")
    list_filter = ("type", "origin", "season")
    search_fields = ("title", "studios")


@admin.register(MangaTitle)
class MangaAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "year", "members", "score")
    list_filter = ("type",)
    search_fields = ("title",)


@admin.register(MarketRecord)
class MarketAdmin(admin.ModelAdmin):
    list_display = ("year", "total", "merchandising", "overseas", "streaming", "record_source")


admin.site.register(ProductionMinutes)
