const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const KEY = "exo_token", EMAIL = "exo_email";
const token = () => sessionStorage.getItem(KEY);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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

/* ---------- routing: #/ landing, #/login, #/signup, #/dashboard ... ---------- */
const VIEWS = ["dashboard", "new", "history", "batch", "keys", "account"];
const TITLES = { dashboard: "Dashboard", new: "New analysis", history: "History", batch: "Batch uploads", keys: "API keys", account: "My account" };
let lastTarget = null;

const go = (v) => { location.hash = "#/" + v; };

function route() {
  const path = location.hash.replace(/^#\/?/, "").split("/")[0];
  const authed = !!token();
  let target;
  if (authed) target = VIEWS.includes(path) ? path : "dashboard";
  else target = path === "signup" ? "signup" : (path === "login" || VIEWS.includes(path)) ? "login" : "";

  $("#landing").hidden = target !== "";
  $("#auth").hidden = target !== "login" && target !== "signup";
  $("#app").hidden = !authed;

  if (target === "login" || target === "signup") {
    const signup = target === "signup";
    $("#auth-title").textContent = signup ? "Create your free account" : "Sign in to ExoAnalytica";
    $("#btn-register").classList.toggle("ghost", !signup);
    $("#btn-login").classList.toggle("ghost", signup);
  }
  if (authed) {
    VIEWS.forEach((v) => { $("#view-" + v).hidden = v !== target; });
    $$(".navbtn").forEach((b) => {
      if (b.dataset.go === target) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current");
    });
    $("#page-title").textContent = TITLES[target];
    const email = sessionStorage.getItem(EMAIL) || "";
    $("#user-email").textContent = email;
    $("#account-email").textContent = email || "-";
    $("#user-chip").textContent = (email[0] || "?").toUpperCase();
    if (target === "dashboard" || target === "history") loadHistory();
  }
  if (target !== lastTarget) window.scrollTo(0, 0);
  lastTarget = target;
}
window.addEventListener("hashchange", route);
document.addEventListener("click", (e) => {
  const b = e.target.closest && e.target.closest("[data-go]");
  if (b) go(b.dataset.go);
});

function logout() {
  sessionStorage.removeItem(KEY); sessionStorage.removeItem(EMAIL);
  $("#result").replaceChildren(el("p", { class: "empty panel" }, "Results appear here. Upload a light curve to start."));
  location.hash = "#/";
  route();
}
$("#logout").onclick = logout;
$("#logout2").onclick = logout;

$("#auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const mode = e.submitter.dataset.mode, f = new FormData(e.target), msg = $("#auth-msg");
  msg.textContent = "";
  try {
    const r = await api("/auth/" + mode, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: f.get("email"), password: f.get("password") }) });
    sessionStorage.setItem(KEY, r.access_token);
    sessionStorage.setItem(EMAIL, String(f.get("email")));
    e.target.reset();
    go("dashboard");
    route();
  } catch (err) { msg.textContent = err.message; }
});

/* ---------- new analysis ---------- */
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
  finally { btn.disabled = false; }
});

async function watch(id) {
  const out = $("#result"), prog = $("#progress"), text = $("#progress-text");
  prog.hidden = false;
  out.replaceChildren();
  try {
    for (;;) {
      const j = await api("/analysis/" + id);
      if (j.status === "done") { prog.hidden = true; render(j.result); return; }
      if (j.status === "failed") { prog.hidden = true; out.replaceChildren(el("p", { class: "msg panel" }, j.error || "Analysis failed.")); return; }
      text.textContent = j.status === "running"
        ? "Running: detrending, searching for transits and scoring them with the CNN…"
        : "Queued: waiting for a free worker…";
      await sleep(2000);
    }
  } catch (e) { prog.hidden = true; throw e; }
}

function openJob(id) {
  go("new");
  route();
  watch(id).catch((e) => { $("#result").replaceChildren(el("p", { class: "msg panel" }, e.message)); });
}

/* ---------- history and dashboard overview ---------- */
async function loadHistory() {
  try {
    const rows = await api("/analysis");
    $("#stat-total").textContent = String(rows.length);
    $("#stat-done").textContent = String(rows.filter((j) => j.status === "done").length);
    $("#stat-fail").textContent = String(rows.filter((j) => j.status === "failed").length);
    const label = (j) => j.target || "Uploaded file";
    const score = (j) => (j.status === "done" && j.score != null ? Math.round(j.score * 100) + "%" : j.status);
    $("#recent").replaceChildren(...(rows.length
      ? rows.slice(0, 5).map((j) => {
        const b = el("button", { type: "button" }, el("span", {}, label(j)), el("span", {}, score(j)));
        b.onclick = () => openJob(j.id);
        return el("li", {}, b);
      })
      : [el("li", { class: "hint" }, "No analyses yet.")]));
    $("#history").replaceChildren(rows.length
      ? table(["Date", "Source", "Status", "CNN confidence"], rows.map((j) => {
        const b = el("button", { type: "button", class: "link" }, new Date(j.created).toLocaleString());
        b.onclick = () => openJob(j.id);
        return [b, label(j), j.status, j.status === "done" && j.score != null ? Math.round(j.score * 100) + "%" : "-"];
      }))
      : el("p", { class: "empty" }, "No analyses yet. Start one from New analysis."));
  } catch { /* shown by api() on 401 */ }
}

/* ---------- charts (plain SVG, no external library) ---------- */
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
function niceTicks(lo, hi, n) {
  const raw = (hi - lo || 1) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) ticks.push(+v.toFixed(10));
  return { ticks, step };
}

function plot(div, x, y, xt, yt, color, shapes) {
  const host = document.getElementById(div);
  const W = 760, H = 340, L = 66, R = 14, T = 12, B = 50;
  const pts = [];
  for (let i = 0; i < x.length; i++) if (Number.isFinite(x[i]) && Number.isFinite(y[i])) pts.push([x[i], y[i]]);
  if (!pts.length) { host.textContent = "No data to plot."; return; }
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  for (const [px, py] of pts) {
    if (px < x0) x0 = px; if (px > x1) x1 = px;
    if (py < y0) y0 = py; if (py > y1) y1 = py;
  }
  const pad = (y1 - y0) * 0.06 || 1e-6; y0 -= pad; y1 += pad;
  if (x1 === x0) x1 = x0 + 1;
  const sx = (v) => L + ((v - x0) / (x1 - x0)) * (W - L - R);
  const sy = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
  const xs = niceTicks(x0, x1, 6), ys = niceTicks(y0, y1, 5);
  const dec = (s) => Math.min(8, Math.max(0, -Math.floor(Math.log10(s))));
  let g = "";
  for (const v of ys.ticks) {
    const yy = sy(v);
    g += `<line x1="${L}" x2="${W - R}" y1="${yy.toFixed(1)}" y2="${yy.toFixed(1)}" style="stroke:var(--rule)"/>`
      + `<text x="${L - 8}" y="${(yy + 4).toFixed(1)}" text-anchor="end" style="fill:var(--mute)">${v.toFixed(dec(ys.step))}</text>`;
  }
  for (const v of xs.ticks) {
    const xx = sx(v);
    g += `<line x1="${xx.toFixed(1)}" x2="${xx.toFixed(1)}" y1="${T}" y2="${H - B}" style="stroke:var(--rule);opacity:.5"/>`
      + `<text x="${xx.toFixed(1)}" y="${H - B + 18}" text-anchor="middle" style="fill:var(--mute)">${v.toFixed(dec(xs.step))}</text>`;
  }
  for (const s of shapes || []) {
    if (s.x0 < x0 || s.x0 > x1) continue;
    const xx = sx(s.x0).toFixed(1);
    g += `<line x1="${xx}" x2="${xx}" y1="${T}" y2="${H - B}" style="stroke:${s.line.color};stroke-dasharray:3 3"/>`;
  }
  g += pts.map(([px, py]) => `<circle cx="${sx(px).toFixed(1)}" cy="${sy(py).toFixed(1)}" r="1.8" style="fill:${color}"/>`).join("");
  g += `<text x="${(L + (W - L - R) / 2).toFixed(0)}" y="${H - 8}" text-anchor="middle" style="fill:var(--ink)">${xt}</text>`
    + `<text transform="translate(16 ${(T + (H - T - B) / 2).toFixed(0)}) rotate(-90)" text-anchor="middle" style="fill:var(--ink)">${yt}</text>`;
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" height="100%" role="img" aria-label="${yt} against ${xt}" style="font:12px 'Hanken Grotesk',sans-serif">${g}</svg>`;
}

/* ---------- small building blocks ---------- */
function table(head, rows) {
  const t = el("table", {}, el("thead", {}, el("tr", {}, ...head.map((h) => el("th", {}, h)))),
    el("tbody", {}, ...rows.map((r) => el("tr", {}, ...r.map((c) => el("td", { class: "num" }, c))))));
  return el("div", { class: "tbl" }, t);
}
const fmt = (v, d = 2) => Number(v).toLocaleString(undefined, { maximumFractionDigits: d });
// Percentage = CNN confidence; label and tone come from the false-positive checks.
const verdictLine = (pct, c) => el("div", { class: "verdict" }, el("strong", { class: c.tone }, pct + "%"),
  el("span", {}, c.label), c.reasons.length ? el("small", {}, "Flagged: " + c.reasons.join(", ")) : "");
const kv = (rows) => el("dl", {}, ...rows.flatMap(([a, b]) => [el("dt", {}, a), el("dd", {}, b)]));

function exportCsv(r) {
  const head = ["signal", "period_d", "depth_ppm", "duration_h", "snr", "snr_correlated_noise", "cnn_confidence", "verdict",
    "radius_earth", "mass_earth", "density_gcc", "gravity_ms2", "semi_major_au", "teq_k", "habitable_zone"];
  const rows = [r, ...(r.planets || [])].map((q, i) => {
    const s = q.signal, p = q.planet;
    return [i + 1, s.period_d, s.depth_ppm, s.duration_h, s.snr, s.snr_red, q.detection.score, q.classification.label,
      p && p.radius_earth, p && p.mass_earth, p && p.density_gcc, p && p.gravity_ms2, p && p.semi_major_au, p && p.teq_k, p && p.hz.status];
  });
  const esc = (v) => { const s = v == null || v === false ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const csv = [head, ...rows].map((row) => row.map(esc).join(",")).join("\n");
  const a = el("a", { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: "exoanalytica-results.csv" });
  document.body.append(a); a.click(); a.remove();
  return csv;
}

function planetSection(r) {
  const signals = [r, ...(r.planets || [])];
  const rows = signals.map((q, i) => q.planet && [String(i + 1), fmt(q.signal.period_d, 3) + " d", fmt(q.planet.radius_earth) + " R⊕",
    fmt(q.planet.mass_earth) + " M⊕", fmt(q.planet.density_gcc) + " g/cm³", fmt(q.planet.gravity_g) + " g",
    fmt(q.planet.teq_k, 0) + " K", q.planet.hz.status]).filter(Boolean);
  const pdf = el("button", { type: "button" }, "Download PDF report");
  pdf.onclick = () => window.print();
  const csv = el("button", { type: "button", class: "ghost" }, "Export CSV data");
  csv.onclick = () => exportCsv(r);
  const sec = el("section", {}, el("div", { class: "toolbar" }, el("h2", {}, "Planet parameters"), el("div", { class: "btns noprint" }, pdf, csv)));
  if (rows.length) {
    sec.append(table(["Signal", "Period", "Radius", "Mass (est.)", "Density", "Gravity", "Equilibrium temp", "Habitable zone"], rows));
    const first = signals.find((q) => q.planet), st = r.stellar;
    sec.append(el("p", { class: "note" }, "Mass uses the " + first.planet.mass_note + ". Star: " + fmt(st.values.radius_rsun) + " R☉ (" + st.source.radius_rsun + "), "
      + fmt(st.values.mass_msun) + " M☉ (" + st.source.mass_msun + "), " + fmt(st.values.teff_k, 0) + " K (" + st.source.teff_k + ")."
      + (signals.some((q) => q.planet && q.planet.gaseous_likely) ? " A planet this large is probably gaseous, so habitable-zone position alone says little about habitability." : "")));
  } else {
    sec.append(el("p", { class: "note" }, "No planet parameters: none of the signals scored as a planet candidate."));
  }
  return sec;
}

function extraSection(o, n, later) {
  const id = "p-fold-" + n, d = o.detection, s = o.signal;
  const sec = el("section", {}, el("h2", {}, "Additional signal " + n + ": " + fmt(s.period_d, 3) + " day period"),
    verdictLine(Math.round(d.score * 100), o.classification),
    el("p", { class: "note" }, "Found after hiding the transits of the stronger signal(s). Extra signals are weaker evidence: check them for stellar variability before trusting them."),
    el("div", { class: "plot js-plot", id }),
    kv([["Period", fmt(s.period_d, 4) + " d"], ["Depth", fmt(s.depth_ppm, 0) + " ppm"], ["Duration", fmt(s.duration_h, 1) + " h"],
      ["Signal-to-noise", fmt(s.snr, 1)], ["SNR with correlated noise", s.snr_red == null ? "-" : fmt(s.snr_red, 1)],
      ["Transits seen", String(o.n_transits)]]));
  sec.append(el("h3", {}, "False-positive checks"));
  for (const fl of o.vetting.flags) sec.append(el("div", { class: "flag " + fl.level }, fl.text));
  later.push(() => plot(id, o.plots.phase_d, o.plots.folded, "Days from mid-transit", "Relative flux", css("--transit")));
  return sec;
}

function render(r) {
  const later = [];
  const out = $("#result"), d = r.detection, s = r.signal;
  const verdict = el("section", {}, verdictLine(Math.round(d.score * 100), r.classification));
  verdict.append(el("p", { class: "note" }, d.method === "cnn"
    ? "The percentage is the CNN's confidence (trained on " + d.trained_on + "). The label combines it with the false-positive checks below. Treat both as screening, not confirmation."
    : "No trained model found; the percentage comes from the transit-search signal-to-noise ratio. The label combines it with the false-positive checks below."));
  if ((r.planets || []).length) {
    verdict.append(el("p", { class: "note" }, "This star shows " + (1 + r.planets.length) + " separate transit signals, so it may host several planets. The strongest is described first."));
  }

  const fold = el("section", {}, el("h2", {}, "Folded at " + fmt(s.period_d, 4) + " days"), el("div", { class: "plot js-plot", id: "p-fold" }));
  const raw = el("section", {}, el("h2", {}, "Detrended light curve"), el("p", { class: "note" }, "Dotted lines mark each transit of the main signal: green where the model is confident, red where it is not. Grey lines are transits of additional signals."), el("div", { class: "plot js-plot", id: "p-raw" }));
  const sig = el("section", {}, el("h2", {}, "Signal"), kv([["Period", fmt(s.period_d, 4) + " d"], ["Depth", fmt(s.depth_ppm, 0) + " ppm"],
    ["Duration", fmt(s.duration_h, 1) + " h"], ["Signal-to-noise", fmt(s.snr, 1)], ["SNR with correlated noise", s.snr_red == null ? "-" : fmt(s.snr_red, 1)]]));
  const parts = [verdict, el("div", { class: "grid2" }, fold, raw), planetSection(r), sig];

  if (r.transits && r.transits.length) {
    const sec = el("section", {}, el("h2", {}, "Individual transits (" + r.n_transits + ")"),
      table(["#", "Time (d)", "Depth (ppm)", "SNR", "Coverage", "Confidence"],
        r.transits.map((x, i) => [String(i + 1), fmt(x.time, 3), fmt(x.depth_ppm, 0), fmt(x.snr, 1), Math.round(x.coverage * 100) + "%", Math.round(x.confidence * 100) + "%"])));
    sec.append(el("p", { class: "note" }, "Each transit is scored on its own. Single transits are noisier than the stacked signal, so faint ones often score low. Low coverage means the transit fell partly in a data gap."
      + (r.n_transits > r.transits.length ? " Showing the first " + r.transits.length + "." : "")));
    parts.push(sec);
  }
  if (r.vetting) {
    const sec = el("section", {}, el("h2", {}, "False-positive checks"),
      el("p", {}, r.vetting.passed ? "No red flags from the automated checks." : "Some checks raised warnings. Read them before trusting this detection."));
    for (const fl of r.vetting.flags) sec.append(el("div", { class: "flag " + fl.level }, fl.text));
    parts.push(sec);
  }
  (r.planets || []).forEach((o, i) => parts.push(extraSection(o, i + 2, later)));
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
  later.forEach((fn) => fn());
  plot("p-fold", r.plots.phase_d, r.plots.folded, "Days from mid-transit", "Relative flux", css("--transit"));
  const marks = (r.transits || []).map((x) => ({ type: "line", x0: x.time, x1: x.time, yref: "paper", y0: 0, y1: 1,
    line: { color: x.confidence >= 0.5 ? css("--ok") : css("--bad"), width: 1, dash: "dot" } }));
  const tmin = r.plots.time[0], tmax = r.plots.time[r.plots.time.length - 1];
  const otherMarks = (r.planets || []).flatMap((o) => {
    const P = o.signal.period_d, e = o.signal.epoch, lines = [];
    for (let k = Math.ceil((tmin - e) / P); e + k * P <= tmax; k++)
      lines.push({ type: "line", x0: e + k * P, x1: e + k * P, yref: "paper", y0: 0, y1: 1, line: { color: css("--mute"), width: 1, dash: "dot" } });
    return lines;
  });
  plot("p-raw", r.plots.time, r.plots.flux, "Time (days)", "Relative flux", css("--ink"), marks.concat(otherMarks));
}

route();