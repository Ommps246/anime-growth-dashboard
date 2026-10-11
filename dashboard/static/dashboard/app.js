/* Small page behaviours + the interactive charts, which read the JSON API. */
const C = {
  pink: "#ff5c9a", cyan: "#38e1d8", yellow: "#ffd166", violet: "#9b7bff", orange: "#ff9457",
  green: "#7be495", blue: "#5aa9ff", grey: "#8a86b0", red: "#ff6b6b",
  ink: "#f3f0ff", muted: "#a9a4cf", grid: "#2b2850", panel: "#131128",
};
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* posters: if an image cannot load, show the title on a gradient card instead */
document.querySelectorAll(".poster img").forEach((img) => {
  const fail = () => { img.closest(".poster").classList.add("noimg"); img.remove(); };
  if (img.complete && img.naturalWidth === 0) fail();
  else img.addEventListener("error", fail, { once: true });
});

/* falling petals */
const petals = document.querySelector(".petals");
if (petals && !reduceMotion) {
  for (let i = 0; i < 14; i++) {
    const p = document.createElement("i");
    p.style.left = Math.random() * 100 + "vw";
    p.style.animationDuration = 11 + Math.random() * 12 + "s";
    p.style.animationDelay = -Math.random() * 20 + "s";
    p.style.scale = 0.6 + Math.random() * 0.9;
    petals.appendChild(p);
  }
}

/* count-up numbers and scroll reveal */
function countUp(el) {
  const target = parseFloat(el.dataset.count);
  const dec = parseInt(el.dataset.dec || "0", 10);
  const fmt = (v) => (el.dataset.pre || "") +
    v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (el.dataset.suf || "");
  if (reduceMotion) { el.textContent = fmt(target); return; }
  const t0 = performance.now(), dur = 1400;
  const tick = (t) => {
    const k = Math.min(1, (t - t0) / dur);
    el.textContent = fmt(target * (1 - Math.pow(1 - k, 3)));
    if (k < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
const io = new IntersectionObserver((entries) => {
  entries.forEach((e) => {
    if (!e.isIntersecting) return;
    e.target.classList.add("in");
    e.target.querySelectorAll("[data-count]").forEach(countUp);
    if (e.target.dataset.count) countUp(e.target);
    io.unobserve(e.target);
  });
}, { threshold: 0.08 });
document.querySelectorAll(".reveal, .kpi").forEach((el) => io.observe(el));

/* ------------------------------------------------------------------ charts */
if (window.Chart) {
  Chart.defaults.color = C.muted;
  Chart.defaults.borderColor = C.grid;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.font.size = 12;
  Chart.defaults.plugins.legend.labels.boxWidth = 12;
  Chart.defaults.plugins.legend.labels.boxHeight = 12;
  Chart.defaults.plugins.legend.labels.color = C.ink;
  Chart.defaults.plugins.tooltip.backgroundColor = "#0a0918";
  Chart.defaults.plugins.tooltip.borderColor = C.grid;
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.animation.duration = reduceMotion ? 0 : 1300;
  Chart.defaults.maintainAspectRatio = false;
}
const nf = (v) => v == null ? "–" : Number(v).toLocaleString("en-US", { maximumFractionDigits: 1 });
const getJSON = (url) => fetch(url).then((r) => r.json());
const noXGrid = { grid: { display: false } };

/* draw each chart only when it scrolls into view, so its animation is seen */
function whenVisible(el, draw) {
  const o = new IntersectionObserver((es) => {
    if (es.some((e) => e.isIntersecting)) { o.disconnect(); draw(); }
  }, { threshold: 0.2 });
  o.observe(el);
}

function forecastChart(canvas) {
  getJSON(canvas.dataset.url).then((f) => {
    const years = f.years.concat(f.future_years);
    const pad = new Array(f.years.length - 1).fill(null);
    const last = f.values[f.values.length - 1];
    new Chart(canvas, {
      type: "line",
      data: {
        labels: years,
        datasets: [
          { label: "Actual", data: f.values, borderColor: C.cyan, backgroundColor: C.cyan, borderWidth: 3, pointRadius: 3, tension: 0.25 },
          { label: "Forecast", data: pad.concat([last], f.forecast), borderColor: C.pink, backgroundColor: C.pink, borderWidth: 3, borderDash: [7, 5], pointRadius: 3, tension: 0.25 },
          { label: "95% prediction interval", data: pad.concat([last], f.high), borderColor: "transparent", backgroundColor: "rgba(255,92,154,.18)", pointRadius: 0, fill: "+1", tension: 0.25 },
          { label: "low", data: pad.concat([last], f.low), borderColor: "transparent", pointRadius: 0, tension: 0.25 },
          { label: "Model fit", data: f.fitted, borderColor: C.grey, borderWidth: 1.5, borderDash: [2, 4], pointRadius: 0, tension: 0.25 },
        ].concat(f.later_years.length ? [{
          label: "Catalogued so far (incomplete)", data: pad.concat([null], f.later_values), showLine: false,
          borderColor: C.muted, backgroundColor: C.muted, pointRadius: 5, pointStyle: "rectRot",
        }] : []),
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: { x: noXGrid, y: { beginAtZero: true, ticks: { callback: (v) => nf(v) }, title: { display: true, text: f.unit } } },
        plugins: {
          legend: { labels: { filter: (i) => i.text !== "low" } },
          tooltip: { filter: (i) => i.dataset.label !== "low", callbacks: { label: (c) => `${c.dataset.label}: ${nf(c.parsed.y)}` } },
        },
      },
    });
  });
}

function productionChart(canvas) {
  getJSON(canvas.dataset.url).then((d) => {
    const colors = { TV: C.pink, MOVIE: C.yellow, OVA: C.violet, ONA: C.cyan, SPECIAL: C.grey };
    const keep = d.years.map((y, i) => (y >= 2000 && y <= d.last_complete_year ? i : -1)).filter((i) => i >= 0);
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: keep.map((i) => d.years[i]),
        datasets: Object.keys(colors).map((k) => ({
          label: d.labels[k], data: keep.map((i) => d.series[k][i]), backgroundColor: colors[k], borderRadius: 2,
        })),
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: { x: { stacked: true, ...noXGrid }, y: { stacked: true, title: { display: true, text: "titles" } } },
        plugins: { tooltip: { callbacks: { footer: (items) => "Total: " + nf(items.reduce((s, i) => s + i.parsed.y, 0)) } } },
      },
    });
  });
}

function marketChart(canvas) {
  getJSON(canvas.dataset.url).then((d) => {
    const order = ["overseas", "merchandising", "pachinko", "streaming", "tv", "live_entertainment", "movie", "video", "music"];
    const colors = { overseas: C.cyan, merchandising: C.pink, streaming: C.yellow, pachinko: C.grey, live_entertainment: C.green, tv: C.violet, movie: C.orange, video: C.blue, music: C.red };
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: d.records.map((r) => r.year),
        datasets: order.map((k) => ({ label: d.segments[k], data: d.records.map((r) => r[k]), backgroundColor: colors[k], borderRadius: 2 })),
      },
      options: {
        interaction: { mode: "index", intersect: false },
        scales: { x: { stacked: true, ...noXGrid }, y: { stacked: true, ticks: { callback: (v) => nf(v) }, title: { display: true, text: "¥ billion" } } },
        plugins: { tooltip: { callbacks: {
          label: (c) => `${c.dataset.label}: ¥${nf(c.parsed.y)}B`,
          footer: (items) => "Total: ¥" + nf(items.reduce((s, i) => s + (i.parsed.y || 0), 0)) + "B",
        } } },
      },
    });
  });
}

const drawers = { forecast: forecastChart, production: productionChart, market: marketChart };
document.querySelectorAll("canvas[data-chart]").forEach((cv) => {
  if (window.Chart) whenVisible(cv, () => drawers[cv.dataset.chart](cv));
});
