/* ERX · tiện ích chung cho trò chơi: số liệu, ngẫu nhiên có hạt giống, biểu đồ SVG, lưu điểm */
(function () {
  "use strict";
  const G = {};

  // ---------- định dạng số kiểu Việt Nam
  G.fmt = (x, d = 0) => (x == null || !isFinite(x)) ? "–" : Number(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  G.pct = (x, d = 1) => (x == null || !isFinite(x)) ? "–" : G.fmt(x * 100, d) + "%";
  G.sgn = (x, d = 1) => (x == null || !isFinite(x)) ? "–" : (x > 0 ? "+" : "") + G.fmt(x, d);
  G.$ = (sel, root) => (root || document).querySelector(sel);
  G.$$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  G.el = (tag, attrs, html) => { const e = document.createElement(tag); if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]); if (html != null) e.innerHTML = html; return e; };
  G.esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ---------- ngẫu nhiên tái lập được (mulberry32)
  G.rng = function (seed) {
    let a = (seed >>> 0) || 1;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  G.normal = function (r) { let u = 0, v = 0; while (u === 0) u = r(); while (v === 0) v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };
  G.seed = () => (Date.now() ^ Math.floor(Math.random() * 1e9)) >>> 0;

  // ---------- thống kê
  G.sum = (a) => a.reduce((s, x) => s + x, 0);
  G.mean = (a) => a.length ? G.sum(a) / a.length : NaN;
  G.variance = (a) => { if (a.length < 2) return 0; const m = G.mean(a); return G.sum(a.map((x) => (x - m) * (x - m))) / (a.length - 1); };
  G.sd = (a) => Math.sqrt(G.variance(a));
  G.normPdf = (z) => Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
  G.normCdf = function (z) { // Zelen & Severo 26.2.17
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const p = 1 - G.normPdf(z) * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z >= 0 ? p : 1 - p;
  };
  G.normInv = function (p) { // Acklam
    if (p <= 0) return -Infinity; if (p >= 1) return Infinity;
    const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
    const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
    const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
    const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
    const pl = 0.02425; let q, r;
    if (p < pl) { q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    if (p > 1 - pl) { q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    q = p - 0.5; r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  };
  G.loss = (z) => G.normPdf(z) - z * (1 - G.normCdf(z)); // hàm tổn thất chuẩn G(z)

  // ---------- màu theo giao diện sáng/tối
  G.css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  G.colors = () => ({ ink: G.css("--ink"), ink2: G.css("--ink-2"), muted: G.css("--muted"), line: G.css("--line"), line2: G.css("--line-2"), bg: G.css("--card"),
    green: G.css("--green"), blue: G.css("--blue"), orange: G.css("--orange"), purple: G.css("--purple"), red: G.css("--red") });
  const themeCbs = [];
  G.onTheme = (cb) => themeCbs.push(cb);
  new MutationObserver(() => themeCbs.forEach((f) => f())).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  if (window.matchMedia) { const mq = window.matchMedia("(prefers-color-scheme: dark)"); (mq.addEventListener ? mq.addEventListener("change", () => themeCbs.forEach((f) => f())) : null); }

  // ---------- trục đẹp
  function niceStep(span, n) { const raw = span / Math.max(1, n); const p = Math.pow(10, Math.floor(Math.log10(raw))); const m = raw / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p; }
  G.niceTicks = function (lo, hi, n = 5) {
    if (!isFinite(lo) || !isFinite(hi)) return { lo: 0, hi: 1, ticks: [0, 1] };
    if (hi - lo < 1e-9) { hi = lo + 1; lo = lo - 1; }
    const st = niceStep(hi - lo, n); const a = Math.floor(lo / st) * st, b = Math.ceil(hi / st) * st; const t = [];
    for (let v = a; v <= b + st / 2; v += st) t.push(Math.round(v / st) * st);
    return { lo: a, hi: b, ticks: t };
  };

  /* ---------- biểu đồ đường SVG
     opts: { labels: [...], series: [{name, data, color, dash, width, step, dots}], bands: [{lo, hi, color, opacity}],
             height, yMin, yMax, yFmt, xEvery, refLines: [{y, label}], vlines: [{x, label}], legend: true, tipFmt } */
  G.lineChart = function (host, opts) {
    const draw = () => {
      const C = G.colors();
      const W = 760, H = opts.height || 280, ml = 58, mr = 16, mt = 14, mb = 34;
      const pw = W - ml - mr, ph = H - mt - mb;
      const n = opts.labels.length;
      let vals = [];
      opts.series.forEach((s) => s.data.forEach((v) => { if (v != null && isFinite(v)) vals.push(v); }));
      (opts.bands || []).forEach((b) => { b.lo.forEach((v) => isFinite(v) && vals.push(v)); b.hi.forEach((v) => isFinite(v) && vals.push(v)); });
      (opts.refLines || []).forEach((r) => vals.push(r.y));
      let lo = opts.yMin != null ? opts.yMin : Math.min(...vals), hi = opts.yMax != null ? opts.yMax : Math.max(...vals);
      if (opts.yMin == null && lo > 0 && lo < (hi - lo) * 0.6) lo = 0;
      const nt = G.niceTicks(lo, hi, 5);
      lo = opts.yMin != null ? opts.yMin : nt.lo; hi = opts.yMax != null ? opts.yMax : nt.hi;
      const X = (i) => ml + (n <= 1 ? pw / 2 : (i * pw) / (n - 1));
      const Y = (v) => mt + ph - ((v - lo) / (hi - lo || 1)) * ph;
      const yFmt = opts.yFmt || ((v) => G.fmt(v));
      let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${G.esc(opts.aria || "Chart")}">`;
      nt.ticks.filter((v) => v >= lo - 1e-9 && v <= hi + 1e-9).forEach((v) => {
        s += `<line x1="${ml}" x2="${W - mr}" y1="${Y(v)}" y2="${Y(v)}" stroke="${C.line2}" stroke-width="1"/>`;
        s += `<text x="${ml - 8}" y="${Y(v) + 4}" text-anchor="end" font-size="12" fill="${C.muted}">${yFmt(v)}</text>`;
      });
      const every = opts.xEvery || Math.max(1, Math.ceil(n / 9));
      opts.labels.forEach((l, i) => { if (i % every === 0 || (i === n - 1 && (n - 1) % every >= Math.max(2, every * 0.8))) s += `<text x="${X(i)}" y="${H - 10}" text-anchor="middle" font-size="12" fill="${C.muted}">${G.esc(l)}</text>`; });
      s += `<line x1="${ml}" x2="${W - mr}" y1="${mt + ph}" y2="${mt + ph}" stroke="${C.line}" stroke-width="1"/>`;
      (opts.vlines || []).forEach((v) => { s += `<line x1="${X(v.x)}" x2="${X(v.x)}" y1="${mt}" y2="${mt + ph}" stroke="${C.muted}" stroke-dasharray="4 4" stroke-width="1"/>` + (v.label ? `<text x="${X(v.x) + 5}" y="${mt + 12}" font-size="11.5" fill="${C.muted}">${G.esc(v.label)}</text>` : ""); });
      (opts.bands || []).forEach((b) => {
        const col = C[b.color] || b.color; let d = "";
        b.hi.forEach((v, i) => { if (isFinite(v)) d += (d ? "L" : "M") + X(i) + " " + Y(v); });
        for (let i = b.lo.length - 1; i >= 0; i--) if (isFinite(b.lo[i])) d += "L" + X(i) + " " + Y(b.lo[i]);
        if (d) s += `<path d="${d}Z" fill="${col}" fill-opacity="${b.opacity || 0.12}" stroke="none"/>`;
      });
      (opts.refLines || []).forEach((r) => { s += `<line x1="${ml}" x2="${W - mr}" y1="${Y(r.y)}" y2="${Y(r.y)}" stroke="${C.muted}" stroke-dasharray="5 4"/>` + (r.label ? `<text x="${W - mr}" y="${Y(r.y) - 5}" text-anchor="end" font-size="11.5" fill="${C.muted}">${G.esc(r.label)}</text>` : ""); });
      opts.series.forEach((se) => {
        const col = C[se.color] || se.color; let d = ""; let pen = false;
        se.data.forEach((v, i) => {
          if (v == null || !isFinite(v)) { pen = false; return; }
          if (se.step && pen) d += "L" + X(i) + " " + Y(se.data[i - 1]);
          d += (pen ? "L" : "M") + X(i) + " " + Y(v); pen = true;
        });
        s += `<path d="${d}" fill="none" stroke="${col}" stroke-width="${se.width || 2}" stroke-linejoin="round" stroke-linecap="round" ${se.dash ? 'stroke-dasharray="6 5"' : ""}/>`;
        if (se.dots) se.data.forEach((v, i) => { if (v != null && isFinite(v)) s += `<circle cx="${X(i)}" cy="${Y(v)}" r="4" fill="${col}" stroke="${C.bg}" stroke-width="2"/>`; });
      });
      s += `<line class="hl" x1="0" x2="0" y1="${mt}" y2="${mt + ph}" stroke="${C.muted}" stroke-width="1" visibility="hidden"/>`;
      s += `<rect class="hit" x="${ml}" y="${mt}" width="${pw}" height="${ph}" fill="transparent"/></svg>`;
      let leg = "";
      if (opts.legend !== false && opts.series.filter((x) => x.name).length > 1) {
        leg = '<div class="g-legend">' + opts.series.filter((x) => x.name).map((x) => `<span style="color:${C[x.color] || x.color}"><i class="${x.dash ? "dash" : ""}"></i><span style="color:${C.ink2}">${G.esc(x.name)}</span></span>`).join("") + "</div>";
      }
      host.innerHTML = leg + `<div class="g-chart">${s}<div class="tip"></div></div>`;
      const svg = host.querySelector("svg"), tip = host.querySelector(".tip"), hl = host.querySelector(".hl"), box = host.querySelector(".g-chart");
      const move = (ev) => {
        const r = svg.getBoundingClientRect(); const cx = ((ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left) * (W / r.width);
        let i = Math.round(((cx - ml) / pw) * (n - 1)); i = Math.max(0, Math.min(n - 1, i));
        hl.setAttribute("x1", X(i)); hl.setAttribute("x2", X(i)); hl.setAttribute("visibility", "visible");
        const rows = opts.series.filter((x) => x.name && x.data[i] != null && isFinite(x.data[i])).map((x) => `<div><span style="color:${C[x.color] || x.color}">●</span> ${G.esc(x.name)}: <b>${(opts.tipFmt || yFmt)(x.data[i])}</b></div>`).join("");
        if (!rows) { tip.style.display = "none"; return; }
        tip.innerHTML = `<div style="color:${C.muted};margin-bottom:2px">${G.esc(opts.labels[i])}</div>` + rows;
        tip.style.display = "block";
        const px = (X(i) / W) * r.width; const tw = tip.offsetWidth;
        tip.style.left = Math.min(Math.max(0, px + 12), r.width - tw) + "px"; tip.style.top = "6px";
      };
      const leave = () => { tip.style.display = "none"; hl.setAttribute("visibility", "hidden"); };
      const hit = host.querySelector(".hit");
      hit.addEventListener("mousemove", move); hit.addEventListener("touchstart", move, { passive: true }); hit.addEventListener("touchmove", move, { passive: true });
      hit.addEventListener("mouseleave", leave); hit.addEventListener("touchend", leave);
    };
    draw();
    G.onTheme(draw);
    return { redraw: draw };
  };

  // ---------- lưu điểm tốt nhất trên trình duyệt (không gửi đi đâu)
  const KEY = "erx_games";
  G.store = {
    all() { try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { return {}; } },
    get(k) { return this.all()[k]; },
    best(k, val, higherIsBetter = true) {
      const a = this.all(); const old = a[k]; let improved = false;
      if (old == null || (higherIsBetter ? val > old.v : val < old.v)) { a[k] = { v: val, t: new Date().toISOString().slice(0, 10) }; improved = true; }
      try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) { /* bỏ qua */ }
      return improved;
    },
  };

  G.seg = function (host, options, value, onChange) {
    host.classList.add("seg"); host.innerHTML = "";
    options.forEach(([v, label]) => {
      const b = G.el("button", { type: "button" }, label); if (v === value) b.classList.add("on");
      b.addEventListener("click", () => { G.$$("button", host).forEach((x) => x.classList.remove("on")); b.classList.add("on"); onChange(v); });
      host.appendChild(b);
    });
  };

  window.G = G;
})();
