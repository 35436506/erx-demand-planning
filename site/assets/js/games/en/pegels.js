/* ERX · Guess the Pegels cell — nhìn chuỗi, xác định dạng trend × seasonality */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const T = ["N", "A", "M"], S = ["N", "A", "M"];
  const TN = { N: "No trend", A: "Additive trend (straight)", M: "Multiplicative trend (curved)" };
  const SN = { N: "No seasonality", A: "Additive seasonality", M: "Multiplicative seasonality" };
  const METHOD = { NN: "SES / Naive", NA: "Seasonal Naive · additive HW without trend", NM: "Multiplicative HW without trend", AN: "Holt (or damped Holt)", AA: "Additive Holt-Winters",
    AM: "Multiplicative Holt-Winters", MN: "Holt on log(y) · multiplicative trend", MA: "Multiplicative trend + additive seasonality (rare)", MM: "Multiplicative Holt-Winters on log, or ETS(M,M,M)" };
  const ROUNDS = 10;
  let level = "easy", round = 0, score = 0, results = [], cur = null, seed = G.seed();
  const MON = ["T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"];

  function gen(r) {
    const tk = T[Math.floor(r() * 3)], sk = S[Math.floor(r() * 3)];
    const n = 36, base = 800 + r() * 600, noise = level === "easy" ? 0.025 : 0.06;
    const slope = base * (0.012 + r() * 0.012), g = 1.022 + r() * 0.012;
    const ampA = base * (0.18 + r() * 0.1), ampM = 0.2 + r() * 0.12, ph = Math.floor(r() * 12), shape = r();
    const tr = [], y = [], lo = [], hi = [], sea = [];
    for (let t = 0; t < n; t++) {
      const k = (t + ph) % 12;
      const sv = Math.sin((2 * Math.PI * k) / 12) + (shape > 0.5 ? 0.45 * Math.sin((4 * Math.PI * k) / 12) : 0);
      sea.push(sv);
      tr.push(tk === "N" ? base : tk === "A" ? base * 0.75 + slope * t : base * 0.55 * Math.pow(g, t));
    }
    const smax = Math.max(...sea.map(Math.abs));
    for (let t = 0; t < n; t++) {
      const e = 1 + G.normal(r) * noise;
      let v = tr[t];
      if (sk === "A") { v = tr[t] + ampA * sea[t]; lo.push(tr[t] - ampA * smax); hi.push(tr[t] + ampA * smax); }
      else if (sk === "M") { v = tr[t] * (1 + ampM * sea[t]); lo.push(tr[t] * (1 - ampM * smax)); hi.push(tr[t] * (1 + ampM * smax)); }
      else { lo.push(NaN); hi.push(NaN); }
      y.push(Math.round(v * e));
    }
    const start = Math.floor(r() * 12);
    const labels = y.map((_, t) => MON[(start + t) % 12] + "/" + (24 + Math.floor((start + t) / 12)));
    return { tk, sk, y, tr, lo, hi, labels };
  }

  function okAnswer(c, tk, sk) {
    if (c.tk !== tk) return false;
    if (c.sk === sk) return true;
    return c.tk === "N" && c.sk !== "N" && sk !== "N"; // không có trend: cộng và nhân trông như nhau
  }

  function setup() {
    root.innerHTML = `<div class="game-panel"><h3>Guess the Pegels cell</h3>
      <p>Each round shows 36 months of one product. Pick the right cell in the Pegels matrix: <strong>trend</strong> (none · additive = straight line · multiplicative = curve) × <strong>seasonality</strong> (none · additive = constant amplitude · multiplicative = amplitude swelling with the sales level).</p>
      <div class="g-row"><span class="g-label" style="width:90px">Difficulty</span><div id="p-lv"></div></div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="p-start">Start ${ROUNDS} rounds</button></div>
      <p class="g-note">Your record: ${(() => { const b = G.store.get("pegels_" + "easy"), h = G.store.get("pegels_" + "hard"); return `Easy ${b ? b.v + "/" + ROUNDS : "–"} · Hard ${h ? h.v + "/" + ROUNDS : "–"}`; })()}</p></div>
      <div class="game-panel"><h3>Four questions when looking at a series</h3><ol class="small" style="margin:0;padding-left:1.2em">
      <li>Does the yearly average rise or fall? Rising by a constant <em>amount</em> → additive; rising by a constant <em>percentage</em> (a curve getting steeper) → multiplicative.</li>
      <li>Do peaks/troughs repeat in the same months every year? → seasonality.</li>
      <li>Does the seasonal amplitude swell as sales grow? → multiplicative seasonality; stays the same → additive.</li>
      <li>Without a trend, additive and multiplicative seasonality look alike — both count as correct.</li></ol></div>`;
    G.seg(G.$("#p-lv"), [["easy", "Easy (little noise)"], ["hard", "Hard (lots of noise)"]], level, (v) => (level = v));
    G.$("#p-start").addEventListener("click", () => { round = 0; score = 0; results = []; seed = G.seed(); next(); });
  }

  function next() {
    const r = G.rng(seed + round * 7919);
    cur = gen(r);
    render(false);
  }

  function render(answered, pick) {
    const dots = Array.from({ length: ROUNDS }, (_, k) => `<i class="${k < results.length ? (results[k] ? "ok" : "no") : k === round ? "cur" : ""}"></i>`).join("");
    const cells = T.map((tk) => `<div class="h">${TN[tk]}</div>` + S.map((sk) => {
      let cls = "";
      if (answered) { if (tk === cur.tk && (sk === cur.sk || okAnswer(cur, tk, sk))) cls = "right"; else if (pick && pick[0] === tk && pick[1] === sk) cls = "wrong"; }
      return `<button type="button" data-t="${tk}" data-s="${sk}" class="${cls}" ${answered ? "disabled" : ""}>${tk},${sk}<br><span style="font-size:.76rem;opacity:.85">${METHOD[tk + sk]}</span></button>`;
    }).join("")).join("");
    root.innerHTML = `<div class="game-wrap"><div>
      <div class="game-panel"><div class="g-row" style="justify-content:space-between"><h3 style="margin:0">Round ${round + 1} / ${ROUNDS}</h3><div class="progress-dots">${dots}</div></div>
        <div id="p-chart" style="margin-top:8px"></div>
        <div id="p-fb"></div></div>
      <div class="game-panel"><h3>Pick the Pegels cell</h3>
        <div class="pgrid"><div class="h"></div>${S.map((sk) => `<div class="h">${SN[sk]}</div>`).join("")}${cells}</div>
        <div class="g-row" style="margin-top:12px">${answered ? `<button class="btn primary" id="p-next">${round + 1 >= ROUNDS ? "See results" : "Next round"} <span class="kbd">Enter</span></button>` : ""}</div></div>
    </div><aside class="game-side"><div class="game-panel"><div class="g-label">Score</div><div class="stat">${score}/${ROUNDS}</div>
      <p class="small muted" style="margin-top:8px">After you choose, the <strong>dashed</strong> line shows the true trend and the <strong>shaded band</strong> shows the seasonal amplitude.</p></div></aside></div>`;
    const series = [{ name: "Demand", data: cur.y, color: "blue", width: 2.2 }];
    const bands = [];
    if (answered) { series.push({ name: "True trend", data: cur.tr, color: "ink", dash: true, width: 2.2 }); if (cur.sk !== "N") bands.push({ lo: cur.lo, hi: cur.hi, color: "orange", opacity: 0.13 }); }
    G.lineChart(G.$("#p-chart"), { labels: cur.labels, series, bands, height: 270, yMin: 0, xEvery: 6, aria: "Demand series to guess" });
    if (!answered) G.$$(".pgrid button").forEach((b) => b.addEventListener("click", () => answer(b.dataset.t, b.dataset.s)));
    else {
      const ok = okAnswer(cur, pick[0], pick[1]);
      const why = [];
      why.push(cur.tk === "N" ? "The base level stays flat across the years." : cur.tk === "A" ? "The base level rises by a constant amount each month — the trend line is a <strong>straight line</strong>." : "The base level rises by a percentage — the trend line <strong>curves ever more steeply</strong>.");
      why.push(cur.sk === "N" ? "No peaks/troughs repeating by month." : cur.sk === "A" ? "The seasonal amplitude stays the same as sales change (parallel band)." : "The seasonal amplitude swells as sales grow (widening band).");
      if (cur.tk === "N" && cur.sk !== "N") why.push("Because there is no trend, additive and multiplicative seasonality look alike — A or M are both correct.");
      G.$("#p-fb").innerHTML = `<div class="g-msg ${ok ? "ok" : "no"}"><strong>${ok ? "Correct!" : "Not quite."}</strong> Answer: cell <strong>(${cur.tk},${cur.sk})</strong> → ${METHOD[cur.tk + cur.sk]}. ${why.join(" ")}</div>`;
      const nb = G.$("#p-next"); nb.focus();
      nb.addEventListener("click", () => { round += 1; if (round >= ROUNDS) finish(); else next(); });
    }
  }

  function answer(tk, sk) {
    const ok = okAnswer(cur, tk, sk);
    if (ok) score += 1;
    results.push(ok);
    render(true, [tk, sk]);
  }

  function finish() {
    const rec = G.store.best("pegels_" + level, score, true);
    root.innerHTML = `<div class="game-panel"><h3>Finished!</h3><div class="tiles"><div class="tile ${score >= 8 ? "good" : ""}"><div class="k">Score</div><div class="v">${score}/${ROUNDS}</div><div class="s">${rec ? "new record" : "record: " + G.store.get("pegels_" + level).v + "/" + ROUNDS}</div></div></div>
      <div class="g-msg ${score >= 8 ? "ok" : ""}">${score >= 8 ? "<strong>Sharp eyes!</strong> You read data very well." : score >= 5 ? "<strong>Quite good.</strong> Common mistakes: confusing additive and multiplicative trend when noise is high, or missing weak seasonality." : "<strong>Needs more practice.</strong> Look at the yearly average level first, then at the amplitude."} Remember the Pegels cell is only a starting point — the final model is always chosen on out-of-sample error (Sessions 3–5).</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="p-again">Play again</button><a class="btn" href="buoi-05.html">Back to Session 5</a></div></div>`;
    G.$("#p-again").addEventListener("click", setup);
  }

  document.addEventListener("keydown", (e) => { if (e.key === "Enter") { const b = G.$("#p-next"); if (b && document.activeElement !== b) b.click(); } });
  setup();
})();
