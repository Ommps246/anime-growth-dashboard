"""Matplotlib figures. Every chart is a function that returns a Figure."""
import io
import threading

import matplotlib

matplotlib.use("Agg")  # draw to memory, no window needed on the server
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

from . import analytics as an  # noqa: E402
from . import forecasting as fc  # noqa: E402

BG, PANEL, INK, MUTED, GRID = "#131128", "#131128", "#f3f0ff", "#a9a4cf", "#2b2850"
PINK, CYAN, YELLOW, VIOLET, ORANGE, GREEN, BLUE, GREY, RED = (
    "#ff5c9a", "#38e1d8", "#ffd166", "#9b7bff", "#ff9457", "#7be495", "#5aa9ff", "#8a86b0", "#ff6b6b")
CYCLE = [PINK, CYAN, YELLOW, VIOLET, ORANGE, GREEN, BLUE, RED, GREY]

TYPE_COLOR = {"TV": PINK, "MOVIE": YELLOW, "OVA": VIOLET, "ONA": CYAN, "SPECIAL": GREY}
SEG_COLOR = {"overseas": CYAN, "merchandising": PINK, "streaming": YELLOW, "pachinko": GREY,
             "live_entertainment": GREEN, "tv": VIOLET, "movie": ORANGE, "video": BLUE, "music": RED}

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": PANEL, "savefig.facecolor": BG,
    "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": GRID, "grid.color": GRID, "axes.grid": True, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.axisbelow": True, "font.size": 13, "axes.titlesize": 16, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.titlepad": 14, "legend.frameon": False,
    "font.family": "DejaVu Sans", "axes.prop_cycle": plt.cycler(color=CYCLE),
    "xtick.major.size": 0, "ytick.major.size": 0,
})


def _fig(w=9.6, h=4.6):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.grid(axis="x", visible=False)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))  # years, never 2012.5
    return fig, ax


def _legend(ax, **kw):
    ax.legend(loc="upper left", ncol=kw.pop("ncol", 3), fontsize=11, handlelength=1.2,
              columnspacing=1.4, labelcolor=INK, **kw)


def _thousands(ax):
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))


def _origin_note(origin):
    return "Japanese titles" if origin == "Japan" else "all origins (Japan, China, Korea)"


# ---------------------------------------------------------------------- shows
def production_stack(origin="Japan"):
    t = an.production_by_year(origin).loc[:an.ANIME_LAST_FULL]
    fig, ax = _fig()
    ax.stackplot(t.index, [t[c] for c in an.TYPE_ORDER], colors=[TYPE_COLOR[c] for c in an.TYPE_ORDER],
                 labels=[an.TYPE_LABEL[c] for c in an.TYPE_ORDER], alpha=0.92, linewidth=0)
    ax.set_title(f"Anime titles released per year, by format — {_origin_note(origin)}")
    ax.set_xlim(t.index.min(), t.index.max())
    ax.set_ylim(0, t["TOTAL"].max() * 1.22)
    _thousands(ax)
    _legend(ax, ncol=5)
    return fig


def tv_series(origin="Japan"):
    t = an.production_by_year(origin)
    full = t.loc[2000:an.ANIME_LAST_FULL, "TV"]
    fig, ax = _fig()
    ax.bar(full.index, full.values, color=PINK, width=0.72)
    nxt = an.ANIME_LAST_FULL + 1
    if nxt in t.index:
        ax.bar([nxt], [t.loc[nxt, "TV"]], color=BG, edgecolor=PINK, linewidth=1.5, hatch="///", width=0.72)
        ax.annotate(f"{nxt}: announced\nso far", (nxt, t.loc[nxt, "TV"]), xytext=(0, 6),
                    textcoords="offset points", ha="center", fontsize=9, color=MUTED)
    peak = full.idxmax()
    ax.annotate(f"{int(full.max())}", (peak, full.max()), xytext=(0, 4), textcoords="offset points",
                ha="center", color=INK, fontweight="bold")
    ax.set_title(f"New TV anime series per year — {_origin_note(origin)}")
    ax.set_ylim(0, max(full.max(), t["TV"].max()) * 1.2)
    return fig


def seasons(origin="Japan"):
    t = an.season_table(origin)
    fig, ax = _fig()
    colors = {"WINTER": BLUE, "SPRING": PINK, "SUMMER": YELLOW, "FALL": ORANGE}
    w = 0.2
    for i, s in enumerate(t.columns):
        ax.bar(t.index + (i - 1.5) * w, t[s], width=w, color=colors[s], label=s.title())
    ax.set_title("TV series by broadcast season")
    ax.set_xticks(t.index)
    ax.set_ylim(0, t.values.max() * 1.25)
    _legend(ax, ncol=4)
    return fig


def studios(origin="Japan"):
    s = an.top_studios(origin).sort_values()
    fig, ax = _fig(9.6, 5.2)
    ax.barh([n.title() for n in s.index], s.values, color=CYAN, height=0.66)
    for y, v in enumerate(s.values):
        ax.text(v + s.max() * 0.01, y, str(int(v)), va="center", color=INK, fontsize=10)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title(f"Most productive studios, TV series and films, 2015–{an.ANIME_LAST_FULL}")
    ax.set_xlim(0, s.max() * 1.1)
    return fig


def genres(origin="Japan"):
    t = an.genre_trend(origin).rolling(3, min_periods=1).mean()
    fig, ax = _fig()
    for i, c in enumerate(t.columns):
        ax.plot(t.index, t[c], color=CYCLE[i % len(CYCLE)], linewidth=2.2, label=c.title())
    ax.set_title("Genre share of each year's titles (3-year average)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylim(0, t.values.max() * 1.3)
    ax.set_xlim(t.index.min(), t.index.max())
    _legend(ax, ncol=4)
    return fig


def scores(origin="Japan"):
    t = an.score_by_year(origin)
    fig, ax = _fig()
    ax.fill_between(t.index, t["p25"], t["p75"], color=VIOLET, alpha=0.3, linewidth=0,
                    label="Middle 50% of series")
    ax.plot(t.index, t["median"], color=YELLOW, linewidth=2.6, label="Median score")
    ax.set_title("Audience score of TV series by release year (out of 10)")
    ax.set_xlim(t.index.min(), t.index.max())
    ax.set_ylim(t["p25"].min() - 0.4, t["p75"].max() + 0.5)
    _legend(ax)
    return fig


def source_material(origin="Japan"):
    t = an.source_material_share(origin)
    order = [c for c in ["Manga", "Light novel", "Game", "Original"] if c in t.columns]
    fig, ax = _fig()
    ax.stackplot(t.index, [t[c] for c in order], labels=order,
                 colors=[PINK, VIOLET, CYAN, YELLOW][:len(order)], alpha=0.92, linewidth=0)
    ax.set_title("What TV anime is adapted from (titles with a known source)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlim(t.index.min(), t.index.max())
    ax.set_ylim(0, 118)
    _legend(ax, ncol=4)
    return fig


def minutes(origin="Japan"):
    t = an.minutes_df()
    fig, ax = _fig()
    ax.fill_between(t["year"], t["minutes"], color=CYAN, alpha=0.18, linewidth=0)
    ax.plot(t["year"], t["minutes"], color=CYAN, linewidth=2.6, marker="o", markersize=4)
    ax.set_title("TV anime minutes produced per year (AJA)")
    ax.set_ylim(0, t["minutes"].max() * 1.15)
    ax.set_xlim(t["year"].min(), t["year"].max())
    ax.set_xticks(range(2000, 2021, 4))
    _thousands(ax)
    return fig


# ---------------------------------------------------------------------- manga
def manga_stack(origin="Japan"):
    t = an.manga_by_year()
    cols = [c for c in t.columns if c != "TOTAL"]
    fig, ax = _fig()
    ax.stackplot(t.index, [t[c] for c in cols], labels=cols,
                 colors=[PINK, VIOLET, GREY, CYAN, YELLOW], alpha=0.92, linewidth=0)
    ax.axvspan(an.MANGA_RELIABLE_END + 0.5, t.index.max(), color=BG, alpha=0.6, linewidth=0)
    ax.axvline(an.MANGA_RELIABLE_END + 0.5, color=MUTED, linestyle="--", linewidth=1)
    ax.text(an.MANGA_RELIABLE_END + 0.7, t["TOTAL"].max() * 1.02, "incomplete:\nnot fully catalogued",
            color=MUTED, fontsize=9, va="bottom")
    ax.set_title("Manga, light novels and manhwa started per year")
    ax.set_xlim(t.index.min(), t.index.max())
    ax.set_ylim(0, t["TOTAL"].max() * 1.28)
    _thousands(ax)
    _legend(ax, ncol=3)
    return fig


def manga_demographics(origin="Japan"):
    t = an.manga_demographics()
    fig, ax = _fig()
    for i, c in enumerate(t.columns):
        ax.plot(t.index, t[c], linewidth=2.4, color=CYCLE[i], label=c)
    ax.set_title(f"Manga launches by target audience, 2000–{an.MANGA_RELIABLE_END}")
    ax.set_xlim(t.index.min(), t.index.max())
    ax.set_ylim(0, t.values.max() * 1.25)
    _legend(ax, ncol=5)
    return fig


def manga_genres(origin="Japan"):
    s = an.manga_genres().sort_values()
    fig, ax = _fig(9.6, 5.0)
    ax.barh(s.index, s.values, color=VIOLET, height=0.66)
    for y, v in enumerate(s.values):
        ax.text(v + s.max() * 0.01, y, f"{int(v):,}", va="center", color=INK, fontsize=10)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    ax.set_title("Most common manga genres, titles started since 2000")
    ax.set_xlim(0, s.max() * 1.12)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    return fig


# --------------------------------------------------------------------- market
def market_stack(origin="Japan"):
    m = an.market_df()
    order = ["overseas", "merchandising", "pachinko", "streaming", "tv", "live_entertainment",
             "movie", "video", "music"]
    fig, ax = _fig(9.6, 5.0)
    bottom = np.zeros(len(m))
    for k in order:
        v = m[k].fillna(0).to_numpy()
        ax.bar(m["year"], v, bottom=bottom, color=SEG_COLOR[k], width=0.78, label=an.SEGMENT_LABEL[k])
        bottom += v
    ax.set_title("Anime industry market by segment (¥ billion)")
    ax.set_ylim(0, m["total"].max() * 1.3)
    _thousands(ax)
    _legend(ax, ncol=5)
    return fig


def market_share(origin="Japan"):
    m = an.market_df()
    sh = an.market_shares()
    fig, ax = _fig()
    for k in ["overseas", "merchandising", "streaming", "video"]:
        ax.plot(m["year"], sh[k], color=SEG_COLOR[k], linewidth=2.6, label=an.SEGMENT_LABEL[k])
        ax.annotate(f"{sh[k].iloc[-1]:.0f}%", (m["year"].iloc[-1], sh[k].iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", color=SEG_COLOR[k], fontweight="bold")
    ax.set_title("Share of the total market")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_xlim(m["year"].min(), m["year"].max() + 1.2)
    ax.set_ylim(0, sh[["overseas", "merchandising"]].max().max() * 1.25)
    _legend(ax, ncol=4)
    return fig


def market_vs_output(origin="Japan"):
    m = an.market_df().set_index("year")
    p = an.production_by_year("Japan")["TOTAL"]
    years = [y for y in m.index if 2005 <= y <= an.ANIME_LAST_FULL]
    base = years[0]
    fig, ax = _fig()
    ax.plot(years, m.loc[years, "total"] / m.loc[base, "total"] * 100, color=CYAN, linewidth=2.8,
            label="Market value")
    ax.plot(years, p.loc[years] / p.loc[base] * 100, color=PINK, linewidth=2.8, label="Titles released")
    ax.axhline(100, color=MUTED, linewidth=1, linestyle=":")
    ax.set_title(f"Market value against output, indexed ({base} = 100)")
    ax.set_xlim(years[0], years[-1])
    _legend(ax)
    return fig


# ------------------------------------------------------------------ forecasts
def forecast_chart(key):
    f = fc.forecast(key)
    fig, ax = _fig()
    ax.plot(f["years"], f["values"], color=CYAN, linewidth=2.6, marker="o", markersize=4, label="Actual")
    ax.plot(f["years"], f["fitted"], color=MUTED, linewidth=1.4, linestyle=":", label="Model fit")
    fx = [f["years"][-1]] + f["future_years"]
    ax.plot(fx, [f["values"][-1]] + f["forecast"], color=PINK, linewidth=2.6, linestyle="--",
            marker="o", markersize=4, label="Forecast")
    ax.fill_between(f["future_years"], f["low"], f["high"], color=PINK, alpha=0.18, linewidth=0,
                    label="95% prediction interval")
    if f["later_years"]:
        ax.plot(f["later_years"], f["later_values"], color=MUTED, linewidth=0, marker="o", markersize=6,
                label="Catalogued so far (incomplete)")
    ax.annotate(f"{f['end_value']:,.0f}", (f["end_year"], f["end_value"]), xytext=(0, 8),
                textcoords="offset points", ha="center", color=INK, fontweight="bold")
    ax.set_title(f"{f['label']} ({f['unit']}) — {f['best']['label'].lower()}")
    ax.set_xlim(f["years"][0], f["end_year"] + 0.6)
    ax.set_ylim(0, max(max(f["high"]), max(f["values"])) * 1.2)
    _thousands(ax)
    _legend(ax, ncol=4)
    return fig


CHARTS = {
    "production_stack": production_stack, "tv_series": tv_series, "seasons": seasons,
    "studios": studios, "genres": genres, "scores": scores, "source_material": source_material,
    "minutes": minutes, "manga_stack": manga_stack, "manga_demographics": manga_demographics,
    "manga_genres": manga_genres, "market_stack": market_stack, "market_share": market_share,
    "market_vs_output": market_vs_output,
}


def build(name, origin="Japan"):
    if name.startswith("forecast_"):
        return forecast_chart(name[len("forecast_"):])
    return CHARTS[name](origin)


_lock = threading.Lock()  # pyplot is not thread-safe and the dev server is threaded


def png(name, origin="Japan"):
    key = ("png", name, origin)
    with _lock:
        if key not in an._cache:
            fig = build(name, origin)
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", pad_inches=0.25)
            plt.close(fig)
            an._cache[key] = buf.getvalue()
    return an._cache[key]


def pdf_report():
    """A multi-page PDF: summary page, then every chart."""
    buf = io.BytesIO()
    k = an.kpis()
    with _lock, PdfPages(buf) as pdf:
        fig = plt.figure(figsize=(11, 7.5))
        fig.text(0.07, 0.86, "ANIME PRODUCTION GROWTH", fontsize=30, fontweight="bold", color=INK)
        fig.text(0.07, 0.80, "Shows, manga and merchandise — Fundamentals of Data Science project",
                 fontsize=13, color=PINK)
        y = 0.70
        for title, text in an.findings():
            fig.text(0.07, y, title, fontsize=12.5, fontweight="bold", color=CYAN)
            words, line, lines = text.split(), "", []
            for w in words:
                if len(line) + len(w) > 118:
                    lines.append(line)
                    line = ""
                line += w + " "
            lines.append(line)
            for i, ln in enumerate(lines):
                fig.text(0.07, y - 0.024 * (i + 1), ln, fontsize=9.5, color=INK)
            y -= 0.024 * (len(lines) + 1) + 0.016
        fig.text(0.07, 0.04, f"Market data to {k['market_year']} (AJA) · titles to {k['titles_year']} "
                 "(anime-offline-database) · manga to 2022 (MyAnimeList). Yen figures in ¥ billion.",
                 fontsize=8.5, color=MUTED)
        pdf.savefig(fig)
        plt.close(fig)
        names = list(CHARTS) + [f"forecast_{s}" for s in fc.SERIES]
        for name in names:
            fig = build(name)
            fig.set_size_inches(11, 6.2)
            if name.startswith("forecast_"):
                f = fc.forecast(name[9:])
                fig.text(0.02, -0.03, f"Model chosen by back-test on the last {f['holdout']} years "
                         f"(error {f['best']['mape']:.1f}%, confidence: {f['confidence'].lower()}).",
                         fontsize=8.5, color=MUTED)
            pdf.savefig(fig, bbox_inches="tight", pad_inches=0.4)
            plt.close(fig)
    return buf.getvalue()
