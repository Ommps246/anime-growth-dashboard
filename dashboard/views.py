import csv
import io
import json

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from . import analytics as an
from . import charts
from . import forecasting as fc
from .forms import JsonImportForm, MarketRecordForm
from .management.commands.load_data import load_market
from .models import MarketRecord, SEGMENTS, SEGMENT_KEYS


def _origin(request):
    return "All" if request.GET.get("origin") == "All" else "Japan"


def _sources():
    with open(settings.DATA_DIR / "sources.json", encoding="utf-8") as fh:
        sources = json.load(fh)
    for s in sources:
        path = settings.DATA_DIR / s["file"]
        s["size_mb"] = path.stat().st_size / 1e6 if path.exists() else 0
    return sources


# ----------------------------------------------------------------------- pages
def overview(request):
    k = an.kpis()
    f = fc.forecast("market_total")
    return render(request, "dashboard/overview.html", {
        "page": "overview", "k": k, "posters": an.poster_wall(),
        "f": f, "top_now": an.top_anime_of_year(an.ANIME_LAST_FULL),
        "findings": an.findings()[:3],
    })


def shows(request):
    origin = _origin(request)
    prod = an.production_by_year(origin)
    last = an.ANIME_LAST_FULL
    ep = an.episodes_by_year(origin)
    stats = [
        (f"{int(prod.loc[last, 'TOTAL']):,}", f"titles released in {last}"),
        (f"{int(prod.loc[last, 'TV']):,}", f"new TV series in {last}"),
        (f"{an.cagr(prod.loc[2000, 'TOTAL'], prod.loc[last, 'TOTAL'], last - 2000):.1f}%",
         "average yearly growth in titles since 2000"),
        (f"{int(ep.loc[last, 'median'])}", f"median episodes per TV series in {last}"),
    ]
    return render(request, "dashboard/shows.html", {
        "page": "shows", "origin": origin, "stats": stats, "last": last,
        "top_now": an.top_anime_of_year(last, 6),
    })


def manga(request):
    t = an.manga_by_year()
    end = an.MANGA_RELIABLE_END
    peak = int(t["TOTAL"].idxmax())
    stats = [
        (f"{int(t.loc[peak, 'TOTAL']):,}", f"titles started in {peak}, the peak year"),
        (f"{an.cagr(t.loc[2000, 'TOTAL'], t.loc[end, 'TOTAL'], end - 2000):.1f}%",
         f"average yearly growth, 2000–{end}"),
        (f"{t.loc[end, 'Light novels'] / t.loc[end, 'TOTAL'] * 100:.0f}%",
         f"of {end} launches were light novels"),
        (f"{an.kpis()['manga_rows']:,}", "titles in the dataset"),
    ]
    return render(request, "dashboard/manga.html", {
        "page": "manga", "stats": stats, "top": an.manga_top(), "reliable_end": end,
    })


def market(request):
    k = an.kpis()
    m = an.market_df().set_index("year")
    y1 = k["market_year"]
    stats = [
        (f"¥{k['market_total_trn']:.2f}T", f"total market in {y1}"),
        (f"¥{k['merch_bn']:.0f}B", f"merchandise in {y1} ({k['merch_yoy']:+.1f}% on the year)"),
        (f"{k['overseas_share']:.0f}%", f"of {y1} revenue came from overseas"),
        (f"×{m.loc[y1, 'streaming'] / m.loc[y1 - 10, 'streaming']:.1f}",
         f"streaming growth since {y1 - 10}"),
    ]
    return render(request, "dashboard/market.html", {
        "page": "market", "stats": stats, "rows": an.market_table()[::-1], "segments": SEGMENTS,
    })


def predictions(request):
    return render(request, "dashboard/predictions.html", {
        "page": "predictions", "forecasts": fc.all_forecasts(), "end": fc.HORIZON_END,
        "holdout": fc.HOLDOUT,
    })


def report(request):
    return render(request, "dashboard/report.html", {
        "page": "report", "k": an.kpis(), "findings": an.findings(),
        "forecasts": fc.all_forecasts(), "end": fc.HORIZON_END, "sources": _sources(),
    })


def data(request):
    form, json_form = MarketRecordForm(), JsonImportForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save":
            form = MarketRecordForm(request.POST)
            if form.is_valid():
                obj = form.save()
                an.clear_cache()
                messages.success(request, f"Saved {obj.year} to SQLite (total ¥{obj.total:,.1f} billion). "
                                          "Charts and predictions now include it.")
                return redirect("dashboard:data")
        elif action == "json":
            json_form = JsonImportForm(request.POST)
            if json_form.is_valid():
                n = json_form.save()
                an.clear_cache()
                messages.success(request, f"Imported {n} record(s) from JSON into SQLite.")
                return redirect("dashboard:data")
        elif action == "reset":
            n = load_market()
            messages.success(request, f"Market table restored from the original CSV ({n} rows).")
            return redirect("dashboard:data")
    k = an.kpis()
    return render(request, "dashboard/data.html", {
        "page": "data", "form": form, "json_form": json_form, "sources": _sources(), "k": k,
        "records": MarketRecord.objects.order_by("-year")[:8],
        "user_rows": MarketRecord.objects.filter(record_source="User entry").count(),
        "next_year": k["market_year"] + 1,
        "json_example": json.dumps([{"year": k["market_year"] + 1, "tv": 99, "movie": 70, "video": 36,
                                     "streaming": 290, "merchandising": 790, "music": 26,
                                     "overseas": 2450, "pachinko": 300, "live_entertainment": 130}],
                                   indent=1),
    })


# ---------------------------------------------------------------- chart images
@require_GET
def chart_png(request, name):
    if name not in charts.CHARTS and name[9:] not in fc.SERIES:
        raise Http404
    return HttpResponse(charts.png(name, _origin(request)), content_type="image/png")


@require_GET
def report_pdf(request):
    resp = HttpResponse(charts.pdf_report(), content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="anime-growth-report.pdf"'
    return resp


# -------------------------------------------------------------------- JSON API
def api_summary(request):
    return JsonResponse(an.kpis())


def api_market(request):
    return JsonResponse({"unit": "billion yen", "segments": dict(SEGMENTS), "records": an.market_table()})


def api_production(request):
    t = an.production_by_year(_origin(request))
    return JsonResponse({
        "origin": _origin(request), "last_complete_year": an.ANIME_LAST_FULL,
        "years": t.index.tolist(), "labels": an.TYPE_LABEL,
        "series": {c: t[c].astype(int).tolist() for c in t.columns},
    })


def api_manga(request):
    t = an.manga_by_year()
    return JsonResponse({
        "reliable_to": an.MANGA_RELIABLE_END, "years": t.index.tolist(),
        "series": {c: t[c].astype(int).tolist() for c in t.columns},
    })


def api_forecast(request, key):
    if key not in fc.SERIES:
        raise Http404
    return JsonResponse(fc.forecast(key))


# ------------------------------------------------------------------- downloads
def _tables():
    prod = an.production_by_year("Japan").reset_index()
    return {
        "market": pd.DataFrame(an.market_table()),
        "forecast": pd.DataFrame(fc.forecast_rows()),
        "production": prod.rename(columns=str.lower),
        "manga": an.manga_by_year().reset_index(),
    }


@require_GET
def download(request, name, fmt):
    tables = _tables()
    if name not in tables or fmt not in ("csv", "json"):
        raise Http404
    df = tables[name]
    if fmt == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False, quoting=csv.QUOTE_MINIMAL)
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
    else:
        resp = HttpResponse(df.to_json(orient="records", indent=2), content_type="application/json")
    resp["Content-Disposition"] = f'attachment; filename="anime_{name}.{fmt}"'
    return resp


@require_GET
def download_raw(request, filename):
    allowed = {s["file"] for s in _sources()}
    if filename not in allowed:
        raise Http404
    return FileResponse(open(settings.DATA_DIR / filename, "rb"), as_attachment=True, filename=filename)
