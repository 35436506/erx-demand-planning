/* ERX · Newsvendor — sản xuất hộp quà Tết once cho cả mùa: bao nhiêu là vừa? */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const ROUNDS = 8;
  const PRODUCTS = ["Phúc Lộc Tết gift box", "An Khang Tết gift basket", "Xuân Sum Vầy biscuit box", "Đoàn Viên Tết seasoning set", "Hưng Thịnh premium Tết gift box",
    "Như Ý Tết candy box", "Tết soft-drink combo", "Vạn Phúc corporate gift box"];
  let seed, round, rounds, plays, total, totalOpt;

  function makeRound(r, k) {
    const mu = Math.round((2000 + r() * 3000) / 50) * 50, cv = 0.2 + r() * 0.2, sigma = Math.round((mu * cv) / 10) * 10;
    const price = Math.round((180 + r() * 220) / 5) * 5, cost = Math.round((price * (0.35 + r() * 0.35)) / 5) * 5, salvage = Math.round((cost * (0.1 + r() * 0.6)) / 5) * 5;
    const cu = price - cost, co = cost - salvage, cr = cu / (cu + co);
    const D = Math.max(0, Math.round(mu + G.normal(r) * sigma));
    return { name: PRODUCTS[k % PRODUCTS.length], mu, sigma, price, cost, salvage, cu, co, cr, D, qstar: Math.max(0, Math.round(mu + G.normInv(cr) * sigma)) };
  }
  const profit = (x, Q) => x.price * Math.min(Q, x.D) + x.salvage * Math.max(Q - x.D, 0) - x.cost * Q;
  function expProfit(x, Q) { // lợi nhuận expected với nhu cầu chuẩn
    const z = (Q - x.mu) / x.sigma, expShort = x.sigma * G.loss(z), expSales = x.mu - expShort, expLeft = Q - expSales;
    return x.price * expSales + x.salvage * expLeft - x.cost * Q;
  }

  function setup() {
    root.innerHTML = `<div class="game-panel"><h3>The Newsvendor problem · producing Tết goods</h3>
      <p>You are in charge of ${ROUNDS} Tết gift products. Each product can be produced only <strong>once</strong> before the season. Too little: lost gross margin. Too much: cleared below cost after Tết. You have a demand forecast (mean and standard deviation) — choose the production quantity.</p>
      <div class="g-row"><button class="btn primary" id="n-start">Start</button></div>
      <p class="g-note">Record: ${(() => { const b = G.store.get("nv_ratio"); return b ? G.fmt(b.v, 1) + "% of the optimal strategy's profit" : "–"; })()}</p></div>
      <div class="game-panel"><h3>Key ideas (Lecture Notes Chapter 11)</h3><ul class="small" style="margin:0;padding-left:1.1em">
      <li>Shortage cost per box: c<sub>u</sub> = price − unit cost. Excess cost per box: c<sub>o</sub> = unit cost − clearance price.</li>
      <li>Critical ratio CR = c<sub>u</sub> / (c<sub>u</sub> + c<sub>o</sub>). The optimal quantity Q* is the CR quantile of the demand distribution: Q* = μ + z<sub>CR</sub>·σ.</li>
      <li>CR &gt; 50% → make more than the mean; CR &lt; 50% → make less than the mean.</li></ul></div>`;
    G.$("#n-start").addEventListener("click", () => { seed = G.seed(); const r = G.rng(seed); rounds = Array.from({ length: ROUNDS }, (_, k) => makeRound(r, k)); round = 0; plays = []; total = 0; totalOpt = 0; render(); });
  }

  function render(last) {
    const x = rounds[round];
    root.innerHTML = `<div class="game-wrap"><div>
      <div class="game-panel"><div class="g-row" style="justify-content:space-between"><h3 style="margin:0">${round + 1}/${ROUNDS} · ${G.esc(x.name)}</h3><div class="progress-dots">${Array.from({ length: ROUNDS }, (_, k) => `<i class="${k < plays.length ? (plays[k].eff >= 0.97 ? "ok" : "no") : k === round ? "cur" : ""}"></i>`).join("")}</div></div>
        <div class="tiles" style="margin-top:12px">
          <div class="tile"><div class="k">Demand forecast</div><div class="v">${G.fmt(x.mu)}</div><div class="s">± ${G.fmt(x.sigma)} (1 standard deviation)</div></div>
          <div class="tile"><div class="k">Price</div><div class="v">${G.fmt(x.price)}</div><div class="s">VND thousand/box</div></div>
          <div class="tile"><div class="k">Unit cost</div><div class="v">${G.fmt(x.cost)}</div><div class="s">VND thousand/box</div></div>
          <div class="tile"><div class="k">Post-Tết clearance</div><div class="v">${G.fmt(x.salvage)}</div><div class="s">VND thousand/box</div></div></div>
        <div class="g-row" style="margin-top:14px"><label class="g-label" for="n-q">Boxes to produce</label><input class="g-input" id="n-q" type="number" min="0" step="50" value="${x.mu}" inputmode="numeric">
          <button class="btn primary" id="n-go">Lock in production <span class="kbd">Enter</span></button><button class="btn sm" id="n-help">Work out shortage / excess cost</button></div>
        <div id="n-helpbox"></div>${last ? lastHtml(last) : ""}</div>
      ${last ? '<div class="game-panel"><h3>Expected profit by production quantity (previous product)</h3><div id="n-curve"></div></div>' : ""}
    </div><aside class="game-side"><div class="game-panel"><div class="g-label">Cumulative profit</div><div class="stat">${G.fmt(total / 1000, 1)}m</div>
      <div class="small muted">Q* strategy (same actual demand): ${G.fmt(totalOpt / 1000, 1)}m</div></div></aside></div>`;
    const q = G.$("#n-q"); q.focus(); q.select();
    const go = () => { const v = parseInt(q.value, 10); if (!(v >= 0)) { q.focus(); return; } submit(v); };
    G.$("#n-go").addEventListener("click", go);
    q.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    G.$("#n-help").addEventListener("click", () => {
      G.$("#n-helpbox").innerHTML = `<div class="g-msg">c<sub>u</sub> = ${G.fmt(x.price)} − ${G.fmt(x.cost)} = <strong>${G.fmt(x.cu)}</strong> · c<sub>o</sub> = ${G.fmt(x.cost)} − ${G.fmt(x.salvage)} = <strong>${G.fmt(x.co)}</strong> → CR = <strong>${G.pct(x.cr, 0)}</strong>. ${x.cr > 0.5 ? "CR > 50%: make more than the mean forecast." : "CR < 50%: make less than the mean forecast."} (Working out Q* is left to you: look up z for the CR in a normal table or use =NORM.S.INV(CR) in Excel.)</div>`;
    });
    if (last) drawCurve(last);
  }

  function lastHtml(p) {
    const x = p.x;
    return `<div class="g-msg ${p.eff >= 0.97 ? "ok" : "no"}" style="margin-top:14px"><strong>${G.esc(x.name)}:</strong> actual demand <strong>${G.fmt(x.D)}</strong>. You made ${G.fmt(p.Q)} → profit <strong>${G.fmt(p.prof / 1000, 1)}m</strong>. Q* = ${G.fmt(x.qstar)} (CR ${G.pct(x.cr, 0)}) → ${G.fmt(p.profOpt / 1000, 1)}m.
      Your <em>expected</em> profit reached ${G.pct(p.eff, 0)} of Q*'s — ${p.eff >= 0.97 ? "a good decision, even though the actual result still depends on luck." : "the gap comes from the decision, not just from luck."}</div>`;
  }

  function drawCurve(p) {
    const x = p.x, lo = Math.max(0, Math.round(x.mu - 3 * x.sigma)), hi = Math.round(x.mu + 3 * x.sigma), step = Math.max(10, Math.round((hi - lo) / 60 / 10) * 10);
    const qs = []; for (let q = lo; q <= hi; q += step) qs.push(q);
    const ep = qs.map((q) => expProfit(x, q) / 1000);
    const near = (v) => qs.reduce((b, q, i) => (Math.abs(q - v) < Math.abs(qs[b] - v) ? i : b), 0);
    const mark = (v) => qs.map((_, i) => (i === near(v) ? ep[i] : null));
    G.lineChart(G.$("#n-curve"), { labels: qs.map((q) => G.fmt(q)), height: 230, xEvery: 10, yFmt: (v) => G.fmt(v, 0), tipFmt: (v) => G.fmt(v, 1) + " tr", series: [
      { name: "Expected profit (VND m)", data: ep, color: "blue" }, { name: "Optimal Q*", data: mark(x.qstar), color: "green", dots: true, width: 0 },
      { name: "Your choice", data: mark(p.Q), color: "orange", dots: true, width: 0 }], aria: "Expected profit" });
  }

  function submit(Q) {
    const x = rounds[round];
    const p = { x, Q, prof: profit(x, Q), profOpt: profit(x, x.qstar), eff: expProfit(x, Q) / expProfit(x, x.qstar) };
    plays.push(p); total += p.prof; totalOpt += p.profOpt; round += 1;
    if (round >= ROUNDS) return finish();
    render(p);
  }

  function finish() {
    const effAvg = G.sum(plays.map((p) => expProfit(p.x, p.Q))) / G.sum(plays.map((p) => expProfit(p.x, p.x.qstar)));
    const rec = G.store.best("nv_ratio", Math.round(effAvg * 1000) / 10, true);
    const rows = plays.map((p, k) => `<tr class="${p.eff >= 0.97 ? "ok" : "no"}"><td>${k + 1}. ${G.esc(p.x.name)}</td><td class="r">${G.pct(p.x.cr, 0)}</td><td class="r">${G.fmt(p.x.mu)}</td><td class="r">${G.fmt(p.Q)}</td><td class="r">${G.fmt(p.x.qstar)}</td><td class="r">${G.fmt(p.x.D)}</td><td class="r">${G.fmt(p.prof / 1000, 1)}</td></tr>`).join("");
    const over = plays.filter((p) => (p.Q - p.x.mu) * (p.x.cr - 0.5) < 0 && Math.abs(p.Q - p.x.mu) > 0.05 * p.x.mu).length;
    root.innerHTML = `<div class="game-panel"><h3>Tết season summary</h3><div class="tiles">
      <div class="tile"><div class="k">Actual profit</div><div class="v">${G.fmt(total / 1000, 1)}m</div></div>
      <div class="tile"><div class="k">Q* strategy</div><div class="v">${G.fmt(totalOpt / 1000, 1)}m</div></div>
      <div class="tile ${effAvg >= 0.97 ? "good" : ""}"><div class="k">Decision quality</div><div class="v">${G.pct(effAvg, 1)}</div><div class="s">${rec ? "new record" : "record: " + G.fmt(G.store.get("nv_ratio").v, 1) + "%"}</div></div></div>
      <div class="g-scroll" style="margin-top:12px"><table class="g-table"><thead><tr><th>Product</th><th class="r">CR</th><th class="r">Forecast μ</th><th class="r">You made</th><th class="r">Q*</th><th class="r">Actual</th><th class="r">Profit (VND m)</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-msg">“Decision quality” compares your <em>expected</em> profit with Q*'s — removing the luck of actual demand. ${over ? `On ${over} products you went <strong>against</strong> the critical ratio (CR > 50% but you made less than the mean, or vice versa).` : "You always followed the direction of the critical ratio."} Research (Schweitzer &amp; Cachon, 2000) shows decision makers tend to choose too close to the mean — “pull-to-centre”.</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="n-again">Play a new season</button><a class="btn" href="buoi-09.html">Back to Session 9</a></div></div>`;
    G.$("#n-again").addEventListener("click", setup);
  }

  setup();
})();
