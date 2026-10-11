from django.urls import path

from . import views

app_name = "dashboard"
urlpatterns = [
    path("", views.overview, name="overview"),
    path("shows/", views.shows, name="shows"),
    path("manga/", views.manga, name="manga"),
    path("market/", views.market, name="market"),
    path("predictions/", views.predictions, name="predictions"),
    path("report/", views.report, name="report"),
    path("data/", views.data, name="data"),
    # matplotlib images
    path("chart/<slug:name>.png", views.chart_png, name="chart"),
    path("report/anime-growth-report.pdf", views.report_pdf, name="report_pdf"),
    # JSON API used by the interactive charts
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/market/", views.api_market, name="api_market"),
    path("api/production/", views.api_production, name="api_production"),
    path("api/manga/", views.api_manga, name="api_manga"),
    path("api/forecast/<slug:key>/", views.api_forecast, name="api_forecast"),
    # downloads
    path("download/raw/<str:filename>", views.download_raw, name="download_raw"),
    path("download/<slug:name>.<slug:fmt>", views.download, name="download"),
]
