/* ERX · Người vs máy — thử thách dự báo 12 months, đo FVA của phán đoán so với Naive, Seasonal Naive and SES */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game"), DATA = (window.GAME_DATA || {}).series || {};
  if (!root) return;
  const KEYS = Object.keys(DATA);
  const START = 24, ALPHA = 0.3;
  let key = KEYS[0], t = START, mine = [], usedHint = [], showHint = false;

  function ses(y, upto) { // dự báo cho kỳ "upto" dùng dữ liệu tới upto-1
    let L = G.mean(y.slice(0, 12));
    for (let i = 0; i < upto; i++) L = ALPHA * y[i] + (1 - ALPHA) * L;
    return L;
  }
  const base = (d, i) => ({ naive: d.y[i - 1], snaive: d.y[i - 12], ses: ses(d.y, i) });
  const wm = (f, a) => G.sum(f.map((v, i) => Math.abs(a[i] - v))) / G.sum(a);
  const bias = (f, a) => G.sum(f.map((v, i) => v - a[i])) / G.sum(a);

  function setup() {
    const opts = KEYS.map((k) => [k, DATA[k].short]);
    root.innerHTML = `<div class="game-panel"><h3>Human vs machine: who forecasts better?</h3>
      <p>You play MBF's Demand Planner. Each round you see the history up to the current month and the business information already known (approved promotions, the Tết calendar). Forecast <strong>the next month</strong>. After 12 rounds, compare your error with three machine methods: <strong>Naive</strong>, <strong>Seasonal Naive</strong> and <strong>SES (α = 0.3)</strong>.</p>
      <div class="g-row"><span class="g-label" style="width:90px">Series</span><div id="f-key"></div></div>
      <p class="small muted" id="f-desc" style="margin-top:8px"></p>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="f-start">Start 12 rounds</button></div>
      <p class="g-note">FVA (Forecast Value Added) = the machine's error − your error. A positive FVA means your judgement <em>really</em> made the forecast better (Session 8).</p></div>`;
    const desc = () => { G.$("#f-desc").innerHTML = G.esc(DATA[key].desc); };
    G.seg(G.$("#f-key"), opts, key, (v) => { key = v; desc(); });
    desc();
    G.$("#f-start").addEventListener("click", () => { t = START; mine = []; usedHint = []; showHint = false; render(); });
  }

  function info(d, i) {
    const out = [];
    out.push(`Same month last year: <strong>${G.fmt(d.y[i - 12])}</strong>`);
    if (d.promo && d.promo[i]) out.push(`Approved promotion next month: <strong>discount ${Math.round(d.promo[i] * 100)}%</strong>` + (d.promo[i - 12] ? ` (same month last year: discount ${Math.round(d.promo[i - 12] * 100)}%)` : ""));
    else if (d.promo) out.push("Next month: no approved promotion");
    if (d.tet && (d.tet[i] > 0 || d.tet_post[i] > 0)) out.push(`Tết calendar next month: ${Math.round(d.tet[i] * 100)}% of pre-Tết shopping days, ${Math.round(d.tet_post[i] * 100)}% after Tết` + (d.tet[i - 12] || d.tet_post[i - 12] ? ` (last year: ${Math.round(d.tet[i - 12] * 100)}% / ${Math.round(d.tet_post[i - 12] * 100)}%)` : ""));
    return out;
  }

  function render() {
    const d = DATA[key];
    const hist = d.y.slice(0, t), lab = d.labels.slice(0, t + 1);
    const myLine = Array(t + 1).fill(null); mine.forEach((v, k) => (myLine[START + k] = v));
    const dots = Array.from({ length: 12 }, (_, k) => `<i class="${k < mine.length ? (Math.abs(mine[k] - d.y[START + k]) / d.y[START + k] <= 0.1 ? "ok" : "no") : k === t - START ? "cur" : ""}"></i>`).join("");
    const b = base(d, t);
    root.innerHTML = `<div class="game-wrap"><div>
      <div class="game-panel"><div class="g-row" style="justify-content:space-between"><h3 style="margin:0">${G.esc(d.short)} · forecast for ${G.esc(d.labels[t])}</h3><div class="progress-dots">${dots}</div></div>
        <div id="f-chart" style="margin-top:6px"></div></div>
      <div class="game-panel"><h3>Known information</h3><ul class="small" style="margin:0 0 10px;padding-left:1.1em">${info(d, t).map((x) => `<li>${x}</li>`).join("")}<li>Last month (${G.esc(d.labels[t - 1])}): <strong>${G.fmt(d.y[t - 1])}</strong></li></ul>
        <div class="g-row"><label class="g-label" for="f-in">Your forecast (cases)</label><input class="g-input" id="f-in" type="number" min="0" step="10" inputmode="numeric">
        <button class="btn primary" id="f-go">Lock in forecast <span class="kbd">Enter</span></button><button class="btn sm" id="f-hint">Show the SES forecast</button></div>
        <div id="f-hintbox">${showHint ? hintHtml(b) : ""}</div>
        <div id="f-last"></div></div>
    </div><aside class="game-side"><div class="game-panel" id="f-score"></div></aside></div>`;
    G.lineChart(G.$("#f-chart"), { labels: lab, height: 260, yMin: 0, xEvery: 3, vlines: [{ x: START, label: "forecast starts" }], series: [
      { name: "Actual", data: hist.concat([null]), color: "ink", width: 2.2 },
      { name: "Your forecast", data: myLine, color: "green", dots: true }], aria: "History and forecast" });
    if (mine.length) {
      const k = mine.length - 1, a = d.y[START + k], f = mine[k], bb = base(d, START + k);
      G.$("#f-last").innerHTML = `<div class="g-msg ${Math.abs(f - a) <= Math.abs(bb.ses - a) ? "ok" : "no"}">Month ${G.esc(d.labels[START + k])}: actual <strong>${G.fmt(a)}</strong> · you ${G.fmt(f)} (off by ${G.pct(Math.abs(f - a) / a, 0)}) · Naive ${G.fmt(bb.naive)} · SNaive ${G.fmt(bb.snaive)} · SES ${G.fmt(bb.ses)}.</div>`;
    }
    scoreBox();
    const inp = G.$("#f-in"); inp.focus();
    const go = () => { const v = parseFloat(inp.value); if (!(v >= 0)) { inp.focus(); return; } mine.push(Math.round(v)); usedHint.push(showHint); showHint = false; t += 1; if (t >= START + 12) finish(); else render(); };
    G.$("#f-go").addEventListener("click", go);
    inp.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    G.$("#f-hint").addEventListener("click", () => { showHint = true; G.$("#f-hintbox").innerHTML = hintHtml(b); });
  }
  const hintHtml = (b) => `<div class="g-msg">SES (α = 0.3) forecasts <strong>${G.fmt(b.ses)}</strong>. Beware of <em>anchoring</em> (): once people have seen the machine's number they tend to adjust very little around it — ask yourself whether the business information is strong enough to justify an adjustment.</div>`;

  function scoreBox() {
    const d = DATA[key], n = mine.length;
    if (!n) { G.$("#f-score").innerHTML = `<div class="g-label">Scoreboard</div><p class="small muted">Your WMAPE and the machine's will update after each round.</p>`; return; }
    const a = d.y.slice(START, START + n);
    const B = { naive: [], snaive: [], ses: [] };
    for (let i = START; i < START + n; i++) { const b = base(d, i); B.naive.push(b.naive); B.snaive.push(b.snaive); B.ses.push(b.ses); }
    const me = wm(mine, a);
    const row = (name, v, hl) => `<tr class="${hl ? "me" : ""}"><td>${name}</td><td class="r">${G.pct(v)}</td></tr>`;
    G.$("#f-score").innerHTML = `<div class="g-label">Scoreboard after ${n} months</div>
      <table class="g-table" style="margin-top:6px"><tbody>${row("You", me, true)}${row("Naive", wm(B.naive, a))}${row("Seasonal Naive", wm(B.snaive, a))}${row("SES", wm(B.ses, a))}</tbody></table>
      <p class="small" style="margin-top:8px">FVA vs SES: <strong style="color:${wm(B.ses, a) - me >= 0 ? "var(--green-ink)" : "var(--red)"}">${G.sgn((wm(B.ses, a) - me) * 100)} % points</strong></p>`;
  }

  function finish() {
    const d = DATA[key], a = d.y.slice(START, START + 12);
    const B = { naive: [], snaive: [], ses: [] };
    for (let i = START; i < START + 12; i++) { const b = base(d, i); B.naive.push(b.naive); B.snaive.push(b.snaive); B.ses.push(b.ses); }
    const me = wm(mine, a), best = Math.min(wm(B.naive, a), wm(B.snaive, a), wm(B.ses, a));
    const rec = G.store.best("fc_" + key, Math.round(me * 1000) / 10, false);
    const hints = usedHint.filter(Boolean).length;
    const rows = [["You", me, bias(mine, a)], ["Naive", wm(B.naive, a), bias(B.naive, a)], ["Seasonal Naive", wm(B.snaive, a), bias(B.snaive, a)], ["SES (α = 0.3)", wm(B.ses, a), bias(B.ses, a)]]
      .map(([nm, w, bs], k) => `<tr class="${k === 0 ? "me" : ""}"><td>${nm}</td><td class="r">${G.pct(w)}</td><td class="r">${G.sgn(bs * 100)}%</td><td class="r">${k === 0 ? "—" : G.sgn((w - me) * 100) + " points"}</td></tr>`).join("");
    const lab = d.labels.slice(0, START + 12);
    const pad = (arr) => Array(START).fill(null).concat(arr);
    root.innerHTML = `<div class="game-panel"><h3>Results · ${G.esc(d.short)}</h3>
      <div class="tiles"><div class="tile ${me <= best ? "good" : "bad"}"><div class="k">Your WMAPE</div><div class="v">${G.pct(me)}</div><div class="s">${rec ? "new record for this series" : "record: " + G.fmt(G.store.get("fc_" + key).v, 1) + "%"}</div></div>
      <div class="tile"><div class="k">Best machine</div><div class="v">${G.pct(best)}</div></div>
      <div class="tile"><div class="k">Your bias</div><div class="v">${G.sgn(bias(mine, a) * 100)}%</div><div class="s">positive = forecast too high</div></div>
      <div class="tile"><div class="k">Times SES was shown</div><div class="v">${hints}/12</div></div></div>
      <div id="f-res" style="margin-top:12px"></div>
      <div class="g-scroll" style="margin-top:12px"><table class="g-table"><thead><tr><th>Method</th><th class="r">WMAPE</th><th class="r">Bias</th><th class="r">Your FVA vs this method</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-msg ${me <= best ? "ok" : "no"}">${me <= best ? "<strong>You beat the machine!</strong> Your judgement added value — thanks to the promotion/Tết information or to luck? Try another series to check." : "<strong>The machine wins.</strong> This is a very common result in research (Fildes et al., 2009): small, poorly grounded adjustments usually make forecasts worse. Only adjust when you have information the machine doesn't."}</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="f-again">Play this series again</button><button class="btn" id="f-other">Choose another series</button></div></div>`;
    G.lineChart(G.$("#f-res"), { labels: lab, height: 260, yMin: 0, xEvery: 3, vlines: [{ x: START }], series: [
      { name: "Actual", data: d.y.slice(0, START + 12), color: "ink", width: 2.4 }, { name: "You", data: pad(mine), color: "green", width: 2.4, dots: true },
      { name: "Naive", data: pad(B.naive), color: "blue", dash: true, width: 1.6 }, { name: "SES", data: pad(B.ses), color: "orange", width: 1.6 }], aria: "Forecast comparison" });
    G.$("#f-again").addEventListener("click", () => { t = START; mine = []; usedHint = []; render(); });
    G.$("#f-other").addEventListener("click", setup);
  }

  if (!KEYS.length) { root.innerHTML = '<p class="muted">Could not load the game data.</p>'; return; }
  setup();
})();
