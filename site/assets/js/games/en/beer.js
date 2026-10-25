/* ERX · Beer Game — trò chơi phân phối bia (Sterman, MIT) phiên bản một người chơi
   Chuỗi 4 khâu: Retailer → Wholesaler → Distributor → Factory. Trễ đơn hàng 1 week, trễ vận chuyển 2 weeks, trễ sản xuất 2 weeks.
   Cost: tồn kho 0,5 / thùng / tuần; nợ đơn (backlog) 1 / thùng / tuần. */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const ROLES = ["Retailer", "Wholesaler", "Distributor", "Factory"];
  const COLORS = ["green", "blue", "orange", "purple"];
  const HOLD = 0.5, BACK = 1.0;

  function demandSeries(weeks, kind, seed) {
    const r = G.rng(seed), d = [];
    for (let t = 0; t < weeks; t++) {
      let v = t < 4 ? 4 : 8;
      if (kind === "noise") v = Math.max(0, Math.round(v + G.normal(r) * 1.2));
      if (kind === "season") v = Math.max(0, Math.round(6 + 3 * Math.sin((2 * Math.PI * t) / 12) + G.normal(r) * 0.8));
      d.push(v);
    }
    return d;
  }

  /* chính sách "máy": neo và điều chỉnh (Sterman 1989).
     classic: dự báo from đơn nhận được, đánh giá thấp hàng đang về (beta nhỏ) → Bullwhip
     chia sẻ: dự báo from nhu cầu khách cuối, tính đủ hàng đang về (beta = 1) */
  function botOrder(st, i, share, custDemand) {
    const theta = 0.4, alpha = 0.3;
    const signal = share ? custDemand : st.incoming[i];
    st.E[i] = theta * signal + (1 - theta) * st.E[i];
    const beta = share ? 1 : 0.35, target = share ? 3 * st.E[i] + 12 : 16.2; // chia sẻ: mục tiêu = hàng đang về cần có (3 tuần) + tồn an toàn 12
    const net = st.inv[i] - st.back[i];
    return Math.max(0, Math.round(st.E[i] + alpha * (target - net - beta * st.onOrder[i])));
  }

  function newState(weeks, demand) {
    const st = { t: 0, weeks, demand, inv: [12, 12, 12, 12], back: [0, 0, 0, 0], ship: [[4, 4], [4, 4], [4, 4], [4, 4]], mail: [[4], [4], [4], [4]],
      onOrder: [12, 12, 12, 12], E: [4, 4, 4, 4], incoming: [4, 4, 4, 4], arrived: [0, 0, 0, 0], cost: [0, 0, 0, 0],
      hist: { orders: [[], [], [], []], inv: [[], [], [], []], back: [[], [], [], []], incoming: [[], [], [], []], cost: [[], [], [], []] } };
    return st;
  }

  // bước 1–3: nhận hàng, nhận đơn, giao hàng
  function beginWeek(st) {
    const t = st.t, shipments = [0, 0, 0, 0];
    for (let i = 0; i < 4; i++) { const a = st.ship[i].shift(); st.inv[i] += a; st.arrived[i] = a; st.onOrder[i] -= a; }
    for (let i = 0; i < 4; i++) {
      const d = i === 0 ? st.demand[t] : st.mail[i].shift();
      st.incoming[i] = d;
      const need = d + st.back[i], s = Math.min(st.inv[i], need);
      st.inv[i] -= s; st.back[i] = need - s; shipments[i] = s;
    }
    for (let i = 1; i < 4; i++) st.ship[i - 1].push(shipments[i]); // hàng đi xuống khâu dưới, tới sau 2 weeks
  }
  // bước 4: đặt hàng, tính chi phí, sang tuần
  function endWeek(st, orders) {
    for (let i = 0; i < 4; i++) {
      const q = Math.max(0, Math.round(orders[i]));
      if (i < 3) st.mail[i + 1].push(q); else st.ship[3].push(q); // nhà máy: lệnh sản xuất xong sau 2 weeks
      st.onOrder[i] += q;
      const c = HOLD * st.inv[i] + BACK * st.back[i]; st.cost[i] += c;
      st.hist.orders[i].push(q); st.hist.inv[i].push(st.inv[i]); st.hist.back[i].push(st.back[i]); st.hist.incoming[i].push(st.incoming[i]); st.hist.cost[i].push(c);
    }
    st.t += 1;
  }
  function simulateAll(weeks, demand, share) {
    const st = newState(weeks, demand);
    while (st.t < weeks) { beginWeek(st); const o = [0, 1, 2, 3].map((i) => botOrder(st, i, share, st.demand[st.t])); endWeek(st, o); }
    return st;
  }
  const bwRatio = (orders, demand) => { const vd = G.variance(demand); return vd > 0 ? G.variance(orders) / vd : NaN; };

  // ---------------------------------------------------------------- giao diện
  let cfg = { role: 0, mode: "classic", weeks: 30, demand: "step" };
  let st = null, seed = 0;

  function setup() {
    root.innerHTML = `
    <div class="game-panel">
      <h3>Game setup</h3>
      <div class="g-row"><span class="g-label" style="width:120px">Your role</span><div id="b-role"></div></div>
      <div class="g-row"><span class="g-label" style="width:120px">Information</span><div id="b-mode"></div></div>
      <div class="g-row"><span class="g-label" style="width:120px">Customer demand</span><div id="b-dem"></div></div>
      <div class="g-row"><span class="g-label" style="width:120px">Weeks</span><div id="b-weeks"></div></div>
      <div class="g-row" style="margin-top:16px"><button class="btn primary" id="b-start">Start the game</button><button class="btn" id="b-auto">Watch the computer play (compare 2 modes)</button></div>
      <p class="g-note">The other three stages are run by the computer using a typical human ordering pattern (Sterman, 1989). Each stage sees only the orders of the stage directly below it — unless sell-out data sharing is switched on.</p>
    </div>
    <div class="game-panel"><h3>Rules</h3>
      <ul class="small" style="padding-left:1.1em;margin:0">
        <li>Each week: receive goods → receive the order from the stage below → ship (any shortfall becomes backlog) → <strong>you decide how many cases to order</strong> from the stage above.</li>
        <li>Orders reach the stage above after <strong>1 week</strong>; shipping takes <strong>2 weeks</strong>; factory production takes <strong>2 weeks</strong>.</li>
        <li>Cost: <strong>0.5</strong> per case in stock per week, <strong>1</strong> per case backlogged per week. Goal: the lowest total cost <em>for the whole chain</em>.</li>
        <li>At the start every stage has 12 cases in stock, 4 cases arriving each week and steady demand of 4 cases/week.</li>
      </ul></div>`;
    G.seg(G.$("#b-role"), ROLES.map((r, i) => [i, r]), cfg.role, (v) => (cfg.role = v));
    G.seg(G.$("#b-mode"), [["classic", "Classic (orders only)"], ["share", "Sell-out data shared"]], cfg.mode, (v) => (cfg.mode = v));
    G.seg(G.$("#b-dem"), [["step", "Step 4 → 8 (classic)"], ["noise", "Step + noise"], ["season", "Seasonal"]], cfg.demand, (v) => (cfg.demand = v));
    G.seg(G.$("#b-weeks"), [[20, "20"], [30, "30"], [40, "40"]], cfg.weeks, (v) => (cfg.weeks = v));
    G.$("#b-start").addEventListener("click", start);
    G.$("#b-auto").addEventListener("click", autoDemo);
  }

  function start() {
    seed = G.seed();
    st = newState(cfg.weeks, demandSeries(cfg.weeks, cfg.demand, seed));
    beginWeek(st);
    renderPlay();
  }

  function suggestion() { // chính sách order-up-to: đặt = mức mục tiêu − inventory position (tồn ròng + hàng đã đặt chưa về)
    const i = cfg.role, share = cfg.mode === "share";
    const recent = share ? st.hist.incoming[0].slice(-3).concat([st.demand[st.t]]) : st.hist.incoming[i].slice(-3).concat([st.incoming[i]]);
    const E = G.mean(recent);
    const S = 4 * E + 12, IP = st.inv[i] - st.back[i] + st.onOrder[i];
    return { q: Math.max(0, Math.round(S - IP)), E, S, IP };
  }

  function renderPlay() {
    const i = cfg.role, share = cfg.mode === "share";
    const nodes = ROLES.map((r, k) => {
      const me = k === i;
      const body = me ? `<div class="d">Stock</div><div class="n">${G.fmt(st.inv[k])}</div><div class="d">Backlog: ${G.fmt(st.back[k])}</div>`
                      : `<div class="d">Computer-run</div><div class="n" style="color:var(--muted)">?</div><div class="d">information hidden</div>`;
      return `<div class="node ${me ? "me" : ""}"><div class="t">${r}${me ? " (you)" : ""}</div>${body}</div>`;
    }).join("");
    const totalMe = st.cost[i];
    root.innerHTML = `
    <div class="game-wrap"><div>
      <div class="game-panel">
        <div class="g-row" style="justify-content:space-between"><h3 style="margin:0">Week ${st.t + 1} / ${st.weeks}</h3><span class="badge ${share ? "" : "orange"}">${share ? "Sell-out data shared" : "Classic"}</span></div>
        <div class="chain" style="margin-top:12px">${nodes}</div>
        <p class="g-note">Customer ← Retailer ← Wholesaler ← Distributor ← Factory (goods flow left, orders flow right).</p>
        <div class="tiles" style="margin-top:10px">
          <div class="tile"><div class="k">Just arrived</div><div class="v">${G.fmt(st.arrived[i])}</div></div>
          <div class="tile"><div class="k">Order just received</div><div class="v">${G.fmt(st.incoming[i])}</div><div class="s">${i === 0 ? "from the customer" : "from " + ROLES[i - 1]}</div></div>
          <div class="tile"><div class="k">In transit</div><div class="v">${G.fmt(st.ship[i][0])} · ${G.fmt(st.ship[i][1])}</div><div class="s">next week · in 2 weeks</div></div>
          <div class="tile"><div class="k">On order, not received</div><div class="v">${G.fmt(st.onOrder[i])}</div><div class="s">supply line</div></div>
          ${share ? `<div class="tile good"><div class="k">End customers bought</div><div class="v">${G.fmt(st.demand[st.t])}</div><div class="s">sell-out data (POS)</div></div>` : ""}
        </div>
        <div class="g-row" style="margin-top:16px">
          <label class="g-label" for="b-q">Order this week</label>
          <input class="g-input" id="b-q" type="number" min="0" step="1" value="${st.incoming[i]}" inputmode="numeric">
          <button class="btn primary" id="b-go">Place order <span class="kbd">Enter</span></button>
          <button class="btn sm" id="b-hint">Formula hint</button>
        </div>
        <div id="b-hintbox"></div>
      </div>
      <div class="game-panel"><h3>Your history</h3><div id="b-chart"></div></div>
    </div>
    <aside class="game-side"><div class="game-panel">
      <div class="g-label">Your cost</div><div class="stat" style="margin:4px 0 10px">${G.fmt(totalMe, 1)}</div>
      <div class="small muted">This week: stock ${G.fmt(st.inv[i])} × 0.5 + backlog ${G.fmt(st.back[i])} × 1 will be charged after you order.</div>
      <hr style="border:0;border-top:1px solid var(--line);margin:14px 0">
      <div class="small"><strong>Demand Planner's tip:</strong> don't forget goods <em>ordered but not yet arrived</em>. Players tend to over-order when short, then get flooded with stock a few weeks later — that is the bullwhip.</div>
      <button class="btn sm" style="margin-top:14px" id="b-quit">End early & see results</button>
    </div></aside></div>`;
    const lab = st.hist.orders[i].map((_, k) => "W" + (k + 1));
    if (lab.length) {
      G.lineChart(G.$("#b-chart"), { labels: lab, height: 230, series: [
        { name: "Orders you received", data: st.hist.incoming[i], color: "muted", dash: true },
        { name: "Orders you placed", data: st.hist.orders[i], color: COLORS[i] },
        { name: "Net inventory (stock − backlog)", data: st.hist.inv[i].map((v, k) => v - st.hist.back[i][k]), color: "red", width: 1.6 }], aria: "Order and inventory history" });
    } else G.$("#b-chart").innerHTML = '<p class="muted small">The chart appears after the first week.</p>';
    const q = G.$("#b-q"); q.focus(); q.select();
    const go = () => { const v = parseInt(q.value, 10); if (!(v >= 0)) { q.focus(); return; } play(v); };
    G.$("#b-go").addEventListener("click", go);
    q.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    G.$("#b-hint").addEventListener("click", () => {
      const h = suggestion();
      G.$("#b-hintbox").innerHTML = `<div class="g-msg">Hint <strong>${h.q}</strong> cases = target level ${G.fmt(h.S, 0)} − inventory position ${G.fmt(h.IP, 0)}. Target level = expected demand ${G.fmt(h.E, 1)} × 4 weeks (1 week order delay + 2 weeks shipping + 1 week cycle) + 12 safety cases; inventory position = stock − backlog + goods on order. The decision is still yours.</div>`;
      q.value = h.q;
    });
    G.$("#b-quit").addEventListener("click", finish);
  }

  function play(q) {
    const orders = [0, 1, 2, 3].map((k) => k === cfg.role ? q : botOrder(st, k, cfg.mode === "share", st.demand[st.t]));
    endWeek(st, orders);
    if (st.t >= st.weeks) return finish();
    beginWeek(st);
    renderPlay();
  }

  function resultBlock(s, title) {
    const n = s.hist.orders[0].length, dem = s.demand.slice(0, n);
    const lab = dem.map((_, k) => "W" + (k + 1));
    const rows = ROLES.map((r, k) => `<tr class="${k === cfg.role && title === null ? "me" : ""}"><td>${r}</td><td class="r">${G.fmt(s.cost[k], 1)}</td><td class="r">${G.fmt(bwRatio(s.hist.orders[k], dem), 1)}</td><td class="r">${G.fmt(Math.max(...s.hist.orders[k]))}</td></tr>`).join("");
    return { lab, dem, rows, total: G.sum(s.cost) };
  }

  function finish() {
    const n = st.hist.orders[0].length;
    if (!n) { setup(); return; }
    const dem = st.demand.slice(0, n);
    const me = resultBlock(st, null);
    const bench = simulateAll(n, dem, true);
    const classic = simulateAll(n, dem, false);
    const improved = G.store.best("beer_cost_" + cfg.role, Math.round(me.total * 10) / 10, false);
    root.innerHTML = `
    <div class="game-panel">
      <h3>Results after ${n} weeks · you played ${ROLES[cfg.role]} (${cfg.mode === "share" ? "data shared" : "classic"})</h3>
      <div class="tiles">
        <div class="tile"><div class="k">Whole-chain cost</div><div class="v">${G.fmt(me.total, 0)}</div><div class="s">${improved ? "your new record for this role" : "record: " + G.fmt(G.store.get("beer_cost_" + cfg.role).v, 0)}</div></div>
        <div class="tile"><div class="k">Your cost</div><div class="v">${G.fmt(st.cost[cfg.role], 0)}</div></div>
        <div class="tile ${bench.cost ? "good" : ""}"><div class="k">Computer · data shared</div><div class="v">${G.fmt(G.sum(bench.cost), 0)}</div><div class="s">same demand, whole chain uses sell-out</div></div>
        <div class="tile bad"><div class="k">Computer · classic</div><div class="v">${G.fmt(G.sum(classic.cost), 0)}</div><div class="s">typical human behaviour</div></div>
      </div>
      <h3 style="margin-top:18px">Each stage's orders vs end-customer demand</h3><div id="r1"></div>
      <h3>Net inventory (stock − backlog)</h3><div id="r2"></div>
      <div class="g-scroll" style="margin-top:12px"><table class="g-table"><thead><tr><th>Stage</th><th class="r">Cost</th><th class="r">Bullwhip ratio</th><th class="r">Largest order</th></tr></thead><tbody>${me.rows}</tbody></table></div>
      <p class="g-note">Bullwhip ratio = variance of the stage's orders ÷ variance of end-customer demand. A ratio that grows towards the factory is the signature of the bullwhip effect.</p>
      <div class="g-msg">${verdict(me.total, G.sum(bench.cost), G.sum(classic.cost))}</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="r-again">Play again</button><button class="btn" id="r-setup">Change role / mode</button></div>
    </div>
    <div class="game-panel"><h3>Discussion questions</h3><ol class="small" style="margin:0;padding-left:1.2em">
      <li>Customer demand rose only once, from 4 to 8. Why do the factory's orders swing so much?</li>
      <li>Did you take into account goods <em>ordered but not yet arrived</em> when deciding? What happens when you forget them?</li>
      <li>How much does sell-out data sharing cut the cost? At MBF, which data is the equivalent (DMS, MT chains' POS)?</li>
      <li>Link to the four causes in Lee et al. (1997) — Lecture Notes section 1.5 and the P&amp;G and Barilla cases in Chapter 20.</li></ol></div>`;
    G.lineChart(G.$("#r1"), { labels: me.lab, height: 270, series: [{ name: "End customer", data: dem, color: "ink", width: 2.6 }].concat(ROLES.map((r, k) => ({ name: r + (k === cfg.role ? " (you)" : ""), data: st.hist.orders[k], color: COLORS[k], width: k === cfg.role ? 2.6 : 1.8 }))), aria: "Orders by stage" });
    G.lineChart(G.$("#r2"), { labels: me.lab, height: 240, refLines: [{ y: 0 }], series: ROLES.map((r, k) => ({ name: r, data: st.hist.inv[k].map((v, j) => v - st.hist.back[k][j]), color: COLORS[k], width: k === cfg.role ? 2.6 : 1.6 })), aria: "Net inventory" });
    G.$("#r-again").addEventListener("click", start);
    G.$("#r-setup").addEventListener("click", setup);
  }

  function verdict(me, share, classic) {
    if (me <= share * 1.1) return "<strong>Excellent!</strong> Your chain came close to the data-sharing benchmark. You accounted for goods in transit and didn't overreact.";
    if (me <= classic) return `<strong>Better than typical behaviour.</strong> But still higher than the data-sharing benchmark by ${G.pct(me / share - 1, 0)} — try again in sharing mode to feel the difference.`;
    return `<strong>The bullwhip has appeared.</strong> The whole-chain cost is higher than the data-sharing benchmark by ${G.pct(me / share - 1, 0)}. Look at the chart: when you ran short, did you over-order and then get flooded a few weeks later?`;
  }

  function autoDemo() {
    const weeks = cfg.weeks, dem = demandSeries(weeks, cfg.demand, G.seed());
    const a = simulateAll(weeks, dem, false), b = simulateAll(weeks, dem, true);
    const lab = dem.map((_, k) => "W" + (k + 1));
    root.innerHTML = `
    <div class="game-panel"><h3>The computer plays: same demand, two ways of operating</h3>
      <div class="tiles"><div class="tile bad"><div class="k">Classic · cost</div><div class="v">${G.fmt(G.sum(a.cost), 0)}</div><div class="s">Factory bullwhip ${G.fmt(bwRatio(a.hist.orders[3], dem), 1)}×</div></div>
      <div class="tile good"><div class="k">Data shared · cost</div><div class="v">${G.fmt(G.sum(b.cost), 0)}</div><div class="s">Factory bullwhip ${G.fmt(bwRatio(b.hist.orders[3], dem), 1)}×</div></div>
      <div class="tile"><div class="k">Saving</div><div class="v">${G.pct(1 - G.sum(b.cost) / G.sum(a.cost), 0)}</div></div></div>
      <h3 style="margin-top:16px">Classic — each stage sees only the orders of the stage below</h3><div id="d1"></div>
      <h3>Sell-out data shared — every stage sees end-customer demand and fully counts goods in transit</h3><div id="d2"></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="d-play">Play it yourself</button><button class="btn" id="d-again">Rerun with new demand</button></div></div>`;
    const ser = (s) => [{ name: "End customer", data: dem, color: "ink", width: 2.6 }].concat(ROLES.map((r, k) => ({ name: r, data: s.hist.orders[k], color: COLORS[k] })));
    const mx = Math.max(...a.hist.orders.flat(), ...b.hist.orders.flat(), ...dem);
    G.lineChart(G.$("#d1"), { labels: lab, height: 250, yMin: 0, yMax: mx, series: ser(a), aria: "Classic" });
    G.lineChart(G.$("#d2"), { labels: lab, height: 250, yMin: 0, yMax: mx, series: ser(b), aria: "Data shared" });
    G.$("#d-play").addEventListener("click", setup);
    G.$("#d-again").addEventListener("click", autoDemo);
  }

  window.__beer = { simulateAll, demandSeries, bwRatio }; // dùng cho kiểm thử
  setup();
})();
