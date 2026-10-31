const $ = (s) => document.querySelector(s);
const KEY = "exo_token";
const token = () => sessionStorage.getItem(KEY);

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  for (const k of kids) n.append(k);
  return n;
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (token()) headers.Authorization = "Bearer " + token();
  const res = await fetch("/api" + path, { ...opts, headers });
  const body = await res.json().catch(() => ({}));
  if (res.status === 401 && token()) { logout(); }
  if (!res.ok) {
    const d = body.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((e) => e.msg).join("; ") : res.status === 429 ? "Too many requests. Wait a moment." : "Request failed.");
  }
  return body;
}

function show() {
  const authed = !!token();
  $("#auth").hidden = authed; $("#app").hidden = !authed; $("#logout").hidden = !authed;
  if (authed) loadHistory();
}
function logout() { sessionStorage.removeItem(KEY); show(); }
$("#logout").onclick = logout;

$("#auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const mode = e.submitter.dataset.mode, f = new FormData(e.target), msg = $("#auth-msg");
  msg.textContent = "";
  try {
    const r = await api("/auth/" + mode, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: f.get("email"), password: f.get("password") }) });
    sessionStorage.setItem(KEY, r.access_token); e.target.reset(); show();
  } catch (err) { msg.textContent = err.message; }
});

let mode = "upload";
function setTab(m) {
  mode = m;
  $("#pane-upload").hidden = m !== "upload"; $("#pane-fetch").hidden = m !== "fetch";
  $("#tab-upload").setAttribute("aria-selected", m === "upload"); $("#tab-fetch").setAttribute("aria-selected", m === "fetch");
}
$("#tab-upload").onclick = () => setTab("upload");
$("#tab-fetch").onclick = () => setTab("fetch");

$("#run-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target), msg = $("#run-msg"), btn = $("#run-btn");
  msg.textContent = ""; btn.disabled = true;
  const num = (k) => (f.get(k) ? Number(f.get(k)) : null);
  try {
    let job;
    if (mode === "upload") {
      const file = f.get("file");
      if (!file || !file.size) throw new Error("Choose a .csv or .fits file.");
      const body = new FormData(); body.append("file", file);
      for (const k of ["radius_rsun", "mass_msun", "teff_k"]) if (f.get(k)) body.append(k, f.get(k));
      if (f.get("injection")) body.append("injection", "true");
      job = await api("/analysis/upload", { method: "POST", body });
    } else {
      job = await api("/analysis/fetch", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target: f.get("target"), mission: f.get("mission"), injection: !!f.get("injection"),
          stellar: { radius_rsun: num("radius_rsun"), mass_msun: num("mass_msun"), teff_k: num("teff_k") } }) });
    }
    await watch(job.id);
  } catch (err) { msg.textContent = err.message; }
  finally { btn.disabled = false; loadHistory(); }
});

async function watch(id) {
  const out = $("#result");
  out.replaceChildren(el("p", { class: "empty" }, "Analysing light curve…"));
  for (;;) {
    const j = await api("/analysis/" + id);
    if (j.status === "done") return render(j.result);
    if (j.status === "failed") { out.replaceChildren(el("p", { class: "msg" }, j.error || "Analysis failed.")); return; }
    await new Promise((r) => setTimeout(r, 2000));
  }
}

async function loadHistory() {
  const ul = $("#history");
  try {
    const rows = await api("/analysis");
    ul.replaceChildren(...rows.map((j) => {
      const label = j.target || "Uploaded file";
      const right = j.status === "done" ? Math.round(j.score * 100) + "%" : j.status;
      const b = el("button", { type: "button" }, el("span", {}, label), el("span", {}, right));
      b.onclick = () => watch(j.id).catch((e) => ($("#result").textContent = e.message));
      return el("li", {}, b);
    }));
    if (!rows.length) ul.replaceChildren(el("li", { class: "hint" }, "No analyses yet."));
  } catch { /* shown by api() on 401 */ }
}

const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
function plot(div, x, y, xt, yt, color, shapes) {
  Plotly.newPlot(div, [{ x, y, mode: "markers", marker: { size: 4, color } }], {
    margin: { t: 10, r: 10, b: 45, l: 60 }, xaxis: { title: xt, gridcolor: css("--rule") }, yaxis: { title: yt, gridcolor: css("--rule") },
    shapes: shapes || [], paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { color: css("--ink"), family: "Hanken Grotesk" },
  }, { displayModeBar: false, responsive: true });
}
function table(head, rows) {
  const t = el("table", {}, el("thead", {}, el("tr", {}, ...head.map((h) => el("th", {}, h)))),
    el("tbody", {}, ...rows.map((r) => el("tr", {}, ...r.map((c) => el("td", { class: "num" }, c))))));
  return el("div", { class: "tbl" }, t);
}
const fmt = (v, d = 2) => Number(v).toLocaleString(undefined, { maximumFractionDigits: d });

function render(r) {
  const out = $("#result"), d = r.detection, s = r.signal, p = r.planet;
  const pct = Math.round(d.score * 100);
  const verdict = el("section", {}, el("div", { class: "verdict" },
    el("strong", { class: d.is_candidate ? "yes" : "no" }, pct + "%"),
    el("span", {}, d.is_candidate ? "Likely planetary transit" : "No convincing transit")));
  verdict.append(el("p", { class: "note" }, d.method === "cnn"
    ? "Scored by a CNN trained on " + d.trained_on + ". Treat as a screening score, not a confirmation."
    : "No trained model found; score comes from the transit-search signal-to-noise ratio."));

  const fold = el("section", {}, el("h2", {}, "Folded at " + fmt(s.period_d, 4) + " days"), el("div", { class: "plot js-plot", id: "p-fold" }));
  const raw = el("section", {}, el("h2", {}, "Detrended light curve"), el("p", { class: "note" }, "Dotted lines mark each transit: green where the model is confident, red where it is not."), el("div", { class: "plot js-plot", id: "p-raw" }));
  const sig = el("section", {}, el("h2", {}, "Signal"), el("dl", {},
    ...[["Period", fmt(s.period_d, 4) + " d"], ["Depth", fmt(s.depth_ppm, 0) + " ppm"], ["Duration", fmt(s.duration_h, 1) + " h"], ["Signal-to-noise", fmt(s.snr, 1)]]
      .flatMap(([a, b]) => [el("dt", {}, a), el("dd", {}, b)])));
  const parts = [verdict, fold, raw, sig];

  if (p) {
    const hz = p.hz, st = r.stellar;
    const rows = [["Radius", fmt(p.radius_earth) + " R⊕ (" + fmt(p.radius_jupiter, 3) + " R♃)"], ["Mass (estimated)", fmt(p.mass_earth) + " M⊕"],
      ["Density", fmt(p.density_gcc) + " g/cm³"], ["Surface gravity", fmt(p.gravity_ms2) + " m/s² (" + fmt(p.gravity_g) + " g)"],
      ["Orbital distance", fmt(p.semi_major_au, 3) + " AU"], ["Equilibrium temperature", fmt(p.teq_k, 0) + " K (albedo 0.3)"],
      ["Habitable zone", hz.status], ["Conservative zone", fmt(hz.inner_cons, 2) + " – " + fmt(hz.outer_cons, 2) + " AU"]];
    const sec = el("section", {}, el("h2", {}, "Planet"), el("dl", {}, ...rows.flatMap(([a, b]) => [el("dt", {}, a), el("dd", {}, b)])));
    sec.append(el("p", { class: "note" }, "Mass uses the " + p.mass_note + ". Star: " + fmt(st.values.radius_rsun) + " R☉ (" + st.source.radius_rsun + "), "
      + fmt(st.values.mass_msun) + " M☉ (" + st.source.mass_msun + "), " + fmt(st.values.teff_k, 0) + " K (" + st.source.teff_k + ")."
      + (p.gaseous_likely ? " A planet this large is probably gaseous, so habitable-zone position alone says little about habitability." : "")));
    parts.push(sec);
  }

  if (r.transits && r.transits.length) {
    const sec = el("section", {}, el("h2", {}, "Individual transits (" + r.n_transits + ")"),
      table(["#", "Time (d)", "Depth (ppm)", "SNR", "Coverage", "Confidence"],
        r.transits.map((x, i) => [String(i + 1), fmt(x.time, 3), fmt(x.depth_ppm, 0), fmt(x.snr, 1), Math.round(x.coverage * 100) + "%", Math.round(x.confidence * 100) + "%"])));
    sec.append(el("p", { class: "note" }, "Each transit is scored on its own. Single transits are noisier than the stacked signal, so faint ones often score low. Low coverage means the transit fell partly in a data gap."
      + (r.n_transits > r.transits.length ? " Showing the first " + r.transits.length + "." : "")));
    parts.push(sec);
  }
  if (r.vetting) {
    const sec = el("section", {}, el("h2", {}, "Vetting"),
      el("p", {}, r.vetting.passed ? "No red flags from the automated checks." : "Some checks raised warnings. Read them before trusting this detection."));
    for (const fl of r.vetting.flags) sec.append(el("div", { class: "flag " + fl.level }, fl.text));
    parts.push(sec);
  }
  if (r.injection) {
    const inj = r.injection, sec = el("section", {}, el("h2", {}, "Injection-recovery test"));
    if (inj.error) sec.append(el("p", { class: "msg" }, inj.error));
    else {
      sec.append(el("p", {}, inj.summary));
      sec.append(el("h3", {}, "Does detrending erase real transits?"));
      sec.append(table(["Transit length", ...inj.windows.map((w) => w + "-day window")],
        inj.retention.map((x) => [x.duration_h + " h", ...inj.windows.map((w) => (x.kept[w] == null ? "-" : Math.round(x.kept[w] * 100) + "% of depth kept"))])));
      sec.append(el("h3", {}, "Does the whole pipeline find them?"));
      sec.append(table(["Injected depth", "Recovered", "Depth measured"],
        inj.recovery.map((x) => [x.depth_ppm + " ppm", x.found + " of " + x.trials, x.depth_kept == null ? "-" : Math.round(x.depth_kept * 100) + "% of injected"])));
      sec.append(el("p", { class: "note" }, "Synthetic transits (periods 1 to 12 days, 2 and 6 hours long) were added to this star's own light curve, with the real signal removed first."));
    }
    parts.push(sec);
  }
  out.replaceChildren(...parts);
  plot("p-fold", r.plots.phase_d, r.plots.folded, "Days from mid-transit", "Relative flux", css("--transit"));
  const marks = (r.transits || []).map((x) => ({ type: "line", x0: x.time, x1: x.time, yref: "paper", y0: 0, y1: 1,
    line: { color: x.confidence >= 0.5 ? css("--ok") : css("--bad"), width: 1, dash: "dot" } }));
  plot("p-raw", r.plots.time, r.plots.flux, "Time (days)", "Relative flux", css("--ink"), marks);
}

show();