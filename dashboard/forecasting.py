"""Trend models and forecasts (NumPy + scikit-learn).

For every series three simple models are fitted on year -> value:
    linear       y = a + b*t
    quadratic    y = a + b*t + c*t^2
    exponential  log(y) = a + b*t      (constant % growth)

The model is chosen by a back-test: hide the last HOLDOUT years, fit on the
rest, and see which model predicts the hidden years with the lowest average
% error (MAPE). The winner is then refitted on all years and projected forward
with a 95% prediction interval from ordinary least squares.
"""
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error, r2_score

from . import analytics as an

HOLDOUT = 4
HORIZON_END = 2030
MODEL_LABEL = {"linear": "Linear trend", "quadratic": "Quadratic trend",
               "exponential": "Exponential (constant % growth)"}

SERIES = {
    "market_total": {"label": "Total anime market", "unit": "¥ billion", "start": 2010, "group": "Market"},
    "merchandising": {"label": "Merchandise", "unit": "¥ billion", "start": 2010, "group": "Market"},
    "overseas": {"label": "Overseas revenue", "unit": "¥ billion", "start": 2013, "group": "Market"},
    "streaming": {"label": "Streaming", "unit": "¥ billion", "start": 2012, "group": "Market"},
    "anime_titles": {"label": "Anime titles released (Japan)", "unit": "titles", "start": 2005, "group": "Shows"},
    "tv_series": {"label": "TV anime series (Japan)", "unit": "series", "start": 2005, "group": "Shows"},
    # The manga data stops in 2022, so this one is a trend check to 2021, not a look ahead to 2030.
    "manga_titles": {"label": "Manga and light novel launches", "unit": "titles", "start": 2000,
                     "group": "Manga", "end": an.MANGA_END},
}


def get_series(key):
    """Return (years, values, note) for the training window of a series."""
    cfg = SERIES[key]
    note = ""
    if key in ("market_total", "merchandising", "overseas", "streaming"):
        m = an.market_df().set_index("year")
        s = m["total" if key == "market_total" else key]
    elif key in ("anime_titles", "tv_series"):
        p = an.production_by_year("Japan")
        s = p["TOTAL" if key == "anime_titles" else "TV"].loc[:an.ANIME_LAST_FULL]
    else:
        s = an.manga_by_year()["TOTAL"].loc[:an.MANGA_RELIABLE_END]
        note = (f"A trend check, not a look ahead. The model is trained on {cfg['start']}–"
                f"{an.MANGA_RELIABLE_END} and carried to {an.MANGA_END}; the grey points are what the "
                "catalogue actually held for those years. The gap is partly titles not yet catalogued "
                "when the data was collected in 2022 and may partly be a real slowdown. This dataset "
                "cannot separate the two, so no 2030 figure is given for manga.")
    s = s.dropna().loc[cfg["start"]:]
    return s.index.to_numpy(dtype=int), s.to_numpy(dtype=float), note


def _design(kind, t):
    """Design matrix: columns 1, t (and t^2 for the quadratic model)."""
    cols = [np.ones_like(t), t] + ([t ** 2] if kind == "quadratic" else [])
    return np.column_stack(cols)


class Trend:
    """One fitted trend model with ordinary-least-squares prediction intervals."""

    def __init__(self, kind, years, values):
        self.kind, self.y0 = kind, years[0]
        self.log = kind == "exponential"
        X = _design(kind, (years - self.y0).astype(float))
        y = np.log(values) if self.log else values.astype(float)
        self.model = LinearRegression(fit_intercept=False).fit(X, y)
        n, p = X.shape
        resid = y - self.model.predict(X)
        self.s2 = float(resid @ resid) / max(n - p, 1)        # residual variance
        self.xtx_inv = np.linalg.pinv(X.T @ X)
        self.tcrit = stats.t.ppf(0.975, max(n - p, 1))        # 95% two-sided

    def predict(self, years):
        X = _design(self.kind, (np.asarray(years) - self.y0).astype(float))
        out = self.model.predict(X)
        return np.exp(out) if self.log else out

    def interval(self, years):
        """95% prediction interval: s * sqrt(1 + x0' (X'X)^-1 x0), widening away from the data."""
        X = _design(self.kind, (np.asarray(years) - self.y0).astype(float))
        mean = self.model.predict(X)
        se = np.sqrt(self.s2 * (1 + np.einsum("ij,jk,ik->i", X, self.xtx_inv, X)))
        low, high = mean - self.tcrit * se, mean + self.tcrit * se
        if self.log:
            return np.exp(low), np.exp(high)
        return np.clip(low, 0, None), high


def _confidence(mape):
    if mape < 8:
        return "Good"
    return "Moderate" if mape < 15 else "Low"


def forecast(key):
    cached = an._cache.get(("forecast", key))
    if cached:
        return cached
    cfg = SERIES[key]
    years, values, note = get_series(key)
    end = cfg.get("end", HORIZON_END)

    # 1. back-test each model on the last HOLDOUT years
    tr_y, tr_v, te_y, te_v = years[:-HOLDOUT], values[:-HOLDOUT], years[-HOLDOUT:], values[-HOLDOUT:]
    scores = []
    for kind in MODEL_LABEL:
        if kind == "exponential" and (values <= 0).any():
            continue
        pred = Trend(kind, tr_y, tr_v).predict(te_y)
        full = Trend(kind, years, values).predict(years)
        scores.append({
            "kind": kind, "label": MODEL_LABEL[kind],
            "mape": mean_absolute_percentage_error(te_v, pred) * 100,
            "mae": float(np.mean(np.abs(te_v - pred))),
            "r2": r2_score(values, full),
        })
    best = min(scores, key=lambda s: s["mape"])
    for s in scores:
        s["best"] = s is best

    # 2. refit the winner on every year and project forward with its interval
    trend = Trend(best["kind"], years, values)
    fitted = trend.predict(years)
    future = np.arange(years[-1] + 1, end + 1)
    point = np.clip(trend.predict(future), 0, None)
    low, high = trend.interval(future)

    # manga only: counts catalogued after the training window, to compare with the trend
    later_years, later_values = [], []
    if key == "manga_titles":
        later = an.manga_by_year()["TOTAL"].loc[years[-1] + 1:end]
        later_years, later_values = later.index.tolist(), [float(v) for v in later.values]

    result = {
        "key": key, "label": cfg["label"], "unit": cfg["unit"], "group": cfg["group"], "note": note,
        "years": years.tolist(), "values": [round(v, 1) for v in values],
        "fitted": [round(v, 1) for v in fitted],
        "future_years": future.tolist(),
        "forecast": [round(v, 1) for v in point],
        "low": [round(v, 1) for v in low], "high": [round(v, 1) for v in high],
        "later_years": later_years, "later_values": later_values,
        "models": scores, "best": best,
        "confidence": "Trend check only" if later_years else _confidence(best["mape"]),
        "train_from": int(years[0]), "train_to": int(years[-1]), "holdout": HOLDOUT,
        "last_year": int(years[-1]), "last_value": float(values[-1]),
        "end_year": int(end), "end_value": float(point[-1]),
        "end_low": float(low[-1]), "end_high": float(high[-1]),
        "change_pct": (float(point[-1]) / float(values[-1]) - 1) * 100,
        "implied_cagr": an.cagr(values[-1], point[-1], end - years[-1]),
    }
    an._cache[("forecast", key)] = result
    return result


def all_forecasts():
    return [forecast(k) for k in SERIES]


def forecast_rows():
    """Flat rows for CSV / JSON export."""
    rows = []
    for f in all_forecasts():
        for y, v, fit in zip(f["years"], f["values"], f["fitted"]):
            rows.append({"series": f["key"], "label": f["label"], "unit": f["unit"], "year": y,
                         "kind": "actual", "value": v, "model_fit": fit, "low": "", "high": "",
                         "model": f["best"]["kind"]})
        for y, v, lo, hi in zip(f["future_years"], f["forecast"], f["low"], f["high"]):
            rows.append({"series": f["key"], "label": f["label"], "unit": f["unit"], "year": y,
                         "kind": "forecast", "value": v, "model_fit": v, "low": lo, "high": hi,
                         "model": f["best"]["kind"]})
    return rows
