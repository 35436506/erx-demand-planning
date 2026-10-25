/* ERX · Thử thách tồn kho — chọn chính sách (s, Q) hoặc (R, S) để đạt fill rate ≥ 98% với chi phí thấp nhất */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const MU = 500, SIG = 150, WEEKS = 52, H = 1, K = 2000, P = 30, TARGET = 0.98, INIT = 1500;
  let seed = 2026, ltVar = false, policy = "sQ", tries = [];
  let par = { s: 900, Q: 600, R: 2, S: 2000 };

  function simulate(pol, p, sd, varLT) {
    const r = G.rng(sd), r2 = G.rng(sd + 99);
    const D = Array.from({ length: WEEKS }, () => Math.max(0, Math.round(MU + G.normal(r) * SIG)));
    const arrivals = Array(WEEKS + 10).fill(0);
    let on = INIT, onOrder = 0, orders = 0, hold = 0, lostQ = 0, sold = 0, stockWeeks = 0;
    const hOn = [], hIP = [], hLost = [], hOrd = [];
    for (let t = 0; t < WEEKS; t++) {
      on += arrivals[t]; onOrder -= arrivals[t];
      const s = Math.min(on, D[t]); const lost = D[t] - s; on -= s; sold += s; lostQ += lost; if (lost > 0) stockWeeks += 1;
      let ip = on + onOrder, q = 0;
      if (pol === "sQ") { while (ip + q <= p.s) q += p.Q; }
      else if (t % p.R === 0) q = Math.max(0, p.S - ip);
      if (q > 0) { const L = varLT ? 1 + Math.floor(r2() * 3) : 2; arrivals[t + L] += q; onOrder += q; orders += 1; }
      hold += H * on;
      hOn.push(on); hIP.push(on + onOrder); hLost.push(lost); hOrd.push(q);
    }
    const totD = G.sum(D);
    return { D, hOn, hIP, hLost, hOrd, fill: sold / totD, cycle: 1 - stockWeeks / WEEKS, avgOn: G.mean(hOn), orders,
      cost: { hold, order: orders * K, lost: lostQ * P, total: hold + orders * K + lostQ * P }, lostQ };
  }

  function theory() {
    const eoq = Math.sqrt((2 * MU * K) / H), L = 2;
    const z95 = G.normInv(0.95), z98 = G.normInv(0.98);
    return { eoq, s95: MU * L + z95 * SIG * Math.sqrt(L), s98: MU * L + z98 * SIG * Math.sqrt(L), S2: MU * (2 + L) + z98 * SIG * Math.sqrt(2 + L), z95, z98 };
  }

  function render(res) {
    const th = theory();
    root.innerHTML = `<div class="game-wrap"><div>
      <div class="game-panel"><h3>Policy setup</h3>
        <div class="g-row"><span class="g-label" style="width:110px">Policy</span><div id="i-pol"></div></div>
        <div class="g-row" id="i-par"></div>
        <div class="g-row"><span class="g-label" style="width:110px">Lead time</span><div id="i-lt"></div></div>
        <div class="g-row" style="margin-top:14px"><button class="btn primary" id="i-run">Run a 52-week simulation <span class="kbd">Enter</span></button><button class="btn sm" id="i-new">New demand</button></div>
        <p class="g-note">Weekly demand ~ Normal(${MU}; ${SIG}) cases. Costs (VND thousand): holding ${H}/case/week · ordering ${G.fmt(K)}/order · lost sale ${P}/case. Opening stock ${G.fmt(INIT)} cases. Goal: <strong>fill rate ≥ ${G.pct(TARGET, 0)}</strong> at the lowest total cost.</p></div>
      <div class="game-panel" id="i-out">${res ? "" : '<p class="muted">Choose the parameters and press run. Each attempt is logged in the table below.</p>'}</div>
      <div class="game-panel"><h3>Attempts</h3><div id="i-tries"></div></div>
    </div><aside class="game-side"><div class="game-panel"><div class="g-label">Theory hints (Chapters 9, 18)</div>
      <ul class="small" style="padding-left:1.1em;margin:8px 0 0">
      <li>EOQ = √(2·D·K/h) = √(2·${MU}·${G.fmt(K)}/${H}) ≈ <strong>${G.fmt(th.eoq)}</strong></li>
      <li>(s, Q): s = μL + zσ√L. With L = 2: z = ${G.fmt(th.z95, 2)} → s ≈ ${G.fmt(th.s95)}; z = ${G.fmt(th.z98, 2)} → s ≈ ${G.fmt(th.s98)}</li>
      <li>(R, S): S = μ(R + L) + zσ√(R + L). R = 2 → S ≈ ${G.fmt(th.S2)}</li>
      <li>Note: the z above is the <em>cycle</em> (service level (α); the fill rate (β) is usually higher than α for the same safety stock.</li></ul>
      <div id="i-best" style="margin-top:12px"></div></div></aside></div>`;
    G.seg(G.$("#i-pol"), [["sQ", "(s, Q) · continuous"], ["RS", "(R, S) · periodic"]], policy, (v) => { policy = v; params(); });
    G.seg(G.$("#i-lt"), [[false, "Fixed 2 weeks"], [true, "Variable 1–3 weeks"]], ltVar, (v) => { ltVar = v; });
    params();
    G.$("#i-run").addEventListener("click", run);
    G.$("#i-new").addEventListener("click", () => { seed = G.seed() % 100000; tries = []; render(); });
    triesTable(); bestBox();
    if (res) out(res);
  }

  function params() {
    const box = G.$("#i-par");
    box.innerHTML = policy === "sQ"
      ? `<span class="g-label" style="width:110px">Parameters</span><label class="small">Reorder point s <input class="g-input" id="p-s" type="number" step="50" min="0" value="${par.s}"></label><label class="small">Order quantity Q <input class="g-input" id="p-Q" type="number" step="50" min="50" value="${par.Q}"></label>`
      : `<span class="g-label" style="width:110px">Parameters</span><label class="small">Review period R (weeks) <input class="g-input" id="p-R" type="number" step="1" min="1" max="8" value="${par.R}"></label><label class="small">Order-up-to level S <input class="g-input" id="p-S" type="number" step="50" min="0" value="${par.S}"></label>`;
    G.$$("input", box).forEach((i) => i.addEventListener("keydown", (e) => { if (e.key === "Enter") run(); }));
  }

  function run() {
    if (policy === "sQ") { par.s = Math.max(0, +G.$("#p-s").value || 0); par.Q = Math.max(50, +G.$("#p-Q").value || 50); }
    else { par.R = Math.min(8, Math.max(1, Math.round(+G.$("#p-R").value || 1))); par.S = Math.max(0, +G.$("#p-S").value || 0); }
    const res = simulate(policy, par, seed, ltVar);
    tries.push({ pol: policy, lab: policy === "sQ" ? `s = ${G.fmt(par.s)}, Q = ${G.fmt(par.Q)}` : `R = ${par.R}, S = ${G.fmt(par.S)}`, lt: ltVar, res });
    if (res.fill >= TARGET && !ltVar) G.store.best("inv_" + seed, Math.round(res.cost.total), false);
    render(res);
  }

  function out(res) {
    const ok = res.fill >= TARGET;
    G.$("#i-out").innerHTML = `<h3>Result of attempt ${tries.length}</h3><div class="tiles">
      <div class="tile ${ok ? "good" : "bad"}"><div class="k">Fill rate (β)</div><div class="v">${G.pct(res.fill)}</div><div class="s">target ≥ ${G.pct(TARGET, 0)}</div></div>
      <div class="tile"><div class="k">Weeks without shortage (α)</div><div class="v">${G.pct(res.cycle, 0)}</div></div>
      <div class="tile"><div class="k">Average stock</div><div class="v">${G.fmt(res.avgOn)}</div><div class="s">cases</div></div>
      <div class="tile"><div class="k">Orders placed</div><div class="v">${res.orders}</div></div>
      <div class="tile ${ok ? "good" : ""}"><div class="k">Total cost</div><div class="v">${G.fmt(res.cost.total / 1000, 1)}</div><div class="s">VND million</div></div></div>
      <p class="small" style="margin-top:8px">Cost: holding ${G.fmt(res.cost.hold / 1000, 1)} m · ordering ${G.fmt(res.cost.order / 1000, 1)} m · lost sales ${G.fmt(res.cost.lost / 1000, 1)}m (${G.fmt(res.lostQ)} cases).</p>
      <div id="i-chart"></div>
      <div class="g-msg ${ok ? "ok" : "no"}">${ok ? "Service target met. Try cutting stock (a lower s or S, or Q closer to EOQ) to lower the cost while keeping ≥ 98%." : "Below 98%: raise the reorder point s (or S) to cover variability during the lead time. Switch on variable lead time to see how much extra safety stock you need."}</div>`;
    const lab = res.D.map((_, i) => "T" + (i + 1));
    G.lineChart(G.$("#i-chart"), { labels: lab, height: 250, yMin: 0, xEvery: 4, series: [
      { name: "On-hand stock", data: res.hOn, color: "green", step: true }, { name: "Inventory position (on hand + in transit)", data: res.hIP, color: "blue", dash: true, width: 1.5, step: true },
      { name: "Demand", data: res.D, color: "muted", width: 1.2 }, { name: "Lost sales", data: res.hLost.map((v) => v > 0 ? v : null), color: "red", dots: true, width: 0 }], aria: "Inventory over time" });
  }

  function triesTable() {
    if (!tries.length) { G.$("#i-tries").innerHTML = '<p class="small muted">No attempts yet.</p>'; return; }
    const best = tries.filter((x) => x.res.fill >= TARGET && !x.lt).reduce((m, x) => (!m || x.res.cost.total < m.res.cost.total ? x : m), null);
    G.$("#i-tries").innerHTML = `<div class="g-scroll"><table class="g-table"><thead><tr><th>#</th><th>Policy</th><th>Lead time</th><th class="r">Fill rate</th><th class="r">Avg stock</th><th class="r">Cost (VND m)</th></tr></thead><tbody>${tries.map((x, k) => `<tr class="${x === best ? "ok me" : x.res.fill < TARGET ? "no" : ""}"><td>${k + 1}</td><td>${x.pol === "sQ" ? "(s, Q)" : "(R, S)"} · ${x.lab}</td><td>${x.lt ? "1–3 weeks" : "2 weeks"}</td><td class="r">${G.pct(x.res.fill)}</td><td class="r">${G.fmt(x.res.avgOn)}</td><td class="r">${G.fmt(x.res.cost.total / 1000, 1)}</td></tr>`).join("")}</tbody></table></div>
      <p class="g-note">The dark green row = the cheapest option meeting the target (fixed lead time). Demand set #${seed} — press “New demand” to try again.</p>`;
  }
  function bestBox() {
    const b = G.store.get("inv_" + seed);
    G.$("#i-best").innerHTML = `<div class="g-label">Your record (demand set #${seed})</div><div class="stat" style="font-size:1.5rem">${b ? G.fmt(b.v / 1000, 1) + "m" : "–"}</div><div class="small muted">lowest cost reaching a fill rate ≥ 98%</div>`;
  }

  document.addEventListener("keydown", (e) => { if (e.key === "Enter" && document.activeElement && document.activeElement.tagName === "BODY") run(); });
  window.__inv = { simulate };
  render();
})();
