/* ERX · Beer Game — trò chơi phân phối bia (Sterman, MIT) phiên bản một người chơi
   Chuỗi 4 khâu: Bán lẻ → Bán buôn → Nhà phân phối → Nhà máy. Trễ đơn hàng 1 tuần, trễ vận chuyển 2 tuần, trễ sản xuất 2 tuần.
   Chi phí: tồn kho 0,5 / thùng / tuần; nợ đơn (backlog) 1 / thùng / tuần. */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const ROLES = ["Bán lẻ", "Bán buôn", "Nhà phân phối", "Nhà máy"];
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
     cổ điển: dự báo từ đơn nhận được, đánh giá thấp hàng đang về (beta nhỏ) → Bullwhip
     chia sẻ: dự báo từ nhu cầu khách cuối, tính đủ hàng đang về (beta = 1) */
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
    for (let i = 1; i < 4; i++) st.ship[i - 1].push(shipments[i]); // hàng đi xuống khâu dưới, tới sau 2 tuần
  }
  // bước 4: đặt hàng, tính chi phí, sang tuần
  function endWeek(st, orders) {
    for (let i = 0; i < 4; i++) {
      const q = Math.max(0, Math.round(orders[i]));
      if (i < 3) st.mail[i + 1].push(q); else st.ship[3].push(q); // nhà máy: lệnh sản xuất xong sau 2 tuần
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
      <h3>Thiết lập ván chơi</h3>
      <div class="g-row"><span class="g-label" style="width:120px">Vai của bạn</span><div id="b-role"></div></div>
      <div class="g-row"><span class="g-label" style="width:120px">Thông tin</span><div id="b-mode"></div></div>
      <div class="g-row"><span class="g-label" style="width:120px">Nhu cầu khách</span><div id="b-dem"></div></div>
      <div class="g-row"><span class="g-label" style="width:120px">Số tuần</span><div id="b-weeks"></div></div>
      <div class="g-row" style="margin-top:16px"><button class="btn primary" id="b-start">Bắt đầu chơi</button><button class="btn" id="b-auto">Xem máy tự chơi (so sánh 2 chế độ)</button></div>
      <p class="g-note">Ba khâu còn lại do máy điều khiển theo cách đặt hàng điển hình của con người (Sterman, 1989). Mỗi khâu chỉ thấy đơn của khâu ngay sau mình — trừ khi bật chế độ chia sẻ dữ liệu bán ra.</p>
    </div>
    <div class="game-panel"><h3>Luật chơi</h3>
      <ul class="small" style="padding-left:1.1em;margin:0">
        <li>Mỗi tuần: nhận hàng về → nhận đơn của khâu sau → giao hàng (thiếu thì ghi nợ đơn) → <strong>bạn quyết định đặt bao nhiêu thùng</strong> lên khâu trên.</li>
        <li>Đơn đặt tới khâu trên sau <strong>1 tuần</strong>; hàng đi đường mất <strong>2 tuần</strong>; nhà máy sản xuất mất <strong>2 tuần</strong>.</li>
        <li>Chi phí: <strong>0,5</strong> mỗi thùng tồn kho/tuần, <strong>1</strong> mỗi thùng nợ đơn/tuần. Mục tiêu: tổng chi phí <em>cả chuỗi</em> thấp nhất.</li>
        <li>Ban đầu mọi khâu có 12 thùng tồn, 4 thùng đang về mỗi tuần, nhu cầu ổn định 4 thùng/tuần.</li>
      </ul></div>`;
    G.seg(G.$("#b-role"), ROLES.map((r, i) => [i, r]), cfg.role, (v) => (cfg.role = v));
    G.seg(G.$("#b-mode"), [["classic", "Cổ điển (chỉ thấy đơn)"], ["share", "Chia sẻ dữ liệu bán ra"]], cfg.mode, (v) => (cfg.mode = v));
    G.seg(G.$("#b-dem"), [["step", "Bậc 4 → 8 (cổ điển)"], ["noise", "Bậc + nhiễu"], ["season", "Mùa vụ"]], cfg.demand, (v) => (cfg.demand = v));
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

  function suggestion() { // chính sách order-up-to: đặt = mức mục tiêu − vị thế tồn kho (tồn ròng + hàng đã đặt chưa về)
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
      const body = me ? `<div class="d">Tồn kho</div><div class="n">${G.fmt(st.inv[k])}</div><div class="d">Nợ đơn: ${G.fmt(st.back[k])}</div>`
                      : `<div class="d">Máy điều khiển</div><div class="n" style="color:var(--muted)">?</div><div class="d">thông tin bị che</div>`;
      return `<div class="node ${me ? "me" : ""}"><div class="t">${r}${me ? " (bạn)" : ""}</div>${body}</div>`;
    }).join("");
    const totalMe = st.cost[i];
    root.innerHTML = `
    <div class="game-wrap"><div>
      <div class="game-panel">
        <div class="g-row" style="justify-content:space-between"><h3 style="margin:0">Tuần ${st.t + 1} / ${st.weeks}</h3><span class="badge ${share ? "" : "orange"}">${share ? "Chia sẻ dữ liệu bán ra" : "Cổ điển"}</span></div>
        <div class="chain" style="margin-top:12px">${nodes}</div>
        <p class="g-note">Khách hàng ← Bán lẻ ← Bán buôn ← Nhà phân phối ← Nhà máy (hàng đi sang trái, đơn đi sang phải).</p>
        <div class="tiles" style="margin-top:10px">
          <div class="tile"><div class="k">Hàng vừa về</div><div class="v">${G.fmt(st.arrived[i])}</div></div>
          <div class="tile"><div class="k">Đơn vừa nhận</div><div class="v">${G.fmt(st.incoming[i])}</div><div class="s">${i === 0 ? "từ khách hàng" : "từ " + ROLES[i - 1]}</div></div>
          <div class="tile"><div class="k">Hàng đang về</div><div class="v">${G.fmt(st.ship[i][0])} · ${G.fmt(st.ship[i][1])}</div><div class="s">tuần sau · 2 tuần nữa</div></div>
          <div class="tile"><div class="k">Đã đặt chưa nhận</div><div class="v">${G.fmt(st.onOrder[i])}</div><div class="s">supply line</div></div>
          ${share ? `<div class="tile good"><div class="k">Khách cuối mua</div><div class="v">${G.fmt(st.demand[st.t])}</div><div class="s">dữ liệu bán ra (POS)</div></div>` : ""}
        </div>
        <div class="g-row" style="margin-top:16px">
          <label class="g-label" for="b-q">Đặt hàng tuần này</label>
          <input class="g-input" id="b-q" type="number" min="0" step="1" value="${st.incoming[i]}" inputmode="numeric">
          <button class="btn primary" id="b-go">Đặt hàng <span class="kbd">Enter</span></button>
          <button class="btn sm" id="b-hint">Gợi ý theo công thức</button>
        </div>
        <div id="b-hintbox"></div>
      </div>
      <div class="game-panel"><h3>Lịch sử của bạn</h3><div id="b-chart"></div></div>
    </div>
    <aside class="game-side"><div class="game-panel">
      <div class="g-label">Chi phí của bạn</div><div class="stat" style="margin:4px 0 10px">${G.fmt(totalMe, 1)}</div>
      <div class="small muted">Tuần này: tồn ${G.fmt(st.inv[i])} × 0,5 + nợ ${G.fmt(st.back[i])} × 1 sẽ được tính sau khi đặt hàng.</div>
      <hr style="border:0;border-top:1px solid var(--line);margin:14px 0">
      <div class="small"><strong>Mẹo của Demand Planner:</strong> đừng quên hàng <em>đã đặt nhưng chưa về</em>. Người chơi thường đặt dồn khi thiếu hàng rồi bị ngập hàng vài tuần sau — chính là Bullwhip.</div>
      <button class="btn sm" style="margin-top:14px" id="b-quit">Kết thúc sớm & xem kết quả</button>
    </div></aside></div>`;
    const lab = st.hist.orders[i].map((_, k) => "T" + (k + 1));
    if (lab.length) {
      G.lineChart(G.$("#b-chart"), { labels: lab, height: 230, series: [
        { name: "Đơn bạn nhận", data: st.hist.incoming[i], color: "muted", dash: true },
        { name: "Đơn bạn đặt", data: st.hist.orders[i], color: COLORS[i] },
        { name: "Tồn kho ròng (tồn − nợ)", data: st.hist.inv[i].map((v, k) => v - st.hist.back[i][k]), color: "red", width: 1.6 }], aria: "Lịch sử đơn hàng và tồn kho" });
    } else G.$("#b-chart").innerHTML = '<p class="muted small">Biểu đồ xuất hiện sau tuần đầu tiên.</p>';
    const q = G.$("#b-q"); q.focus(); q.select();
    const go = () => { const v = parseInt(q.value, 10); if (!(v >= 0)) { q.focus(); return; } play(v); };
    G.$("#b-go").addEventListener("click", go);
    q.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    G.$("#b-hint").addEventListener("click", () => {
      const h = suggestion();
      G.$("#b-hintbox").innerHTML = `<div class="g-msg">Gợi ý <strong>${h.q}</strong> thùng = mức mục tiêu ${G.fmt(h.S, 0)} − vị thế tồn kho ${G.fmt(h.IP, 0)}. Mức mục tiêu = nhu cầu dự kiến ${G.fmt(h.E, 1)} × 4 tuần (1 tuần đơn + 2 tuần vận chuyển + 1 tuần chu kỳ) + 12 thùng an toàn; vị thế tồn kho = tồn − nợ đơn + hàng đã đặt chưa về. Bạn vẫn tự quyết định.</div>`;
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
    const lab = dem.map((_, k) => "T" + (k + 1));
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
      <h3>Kết quả sau ${n} tuần · bạn chơi vai ${ROLES[cfg.role]} (${cfg.mode === "share" ? "chia sẻ dữ liệu" : "cổ điển"})</h3>
      <div class="tiles">
        <div class="tile"><div class="k">Chi phí cả chuỗi</div><div class="v">${G.fmt(me.total, 0)}</div><div class="s">${improved ? "kỷ lục mới của bạn ở vai này" : "kỷ lục: " + G.fmt(G.store.get("beer_cost_" + cfg.role).v, 0)}</div></div>
        <div class="tile"><div class="k">Chi phí của bạn</div><div class="v">${G.fmt(st.cost[cfg.role], 0)}</div></div>
        <div class="tile ${bench.cost ? "good" : ""}"><div class="k">Máy · chia sẻ dữ liệu</div><div class="v">${G.fmt(G.sum(bench.cost), 0)}</div><div class="s">cùng nhu cầu, cả chuỗi dùng sell-out</div></div>
        <div class="tile bad"><div class="k">Máy · cổ điển</div><div class="v">${G.fmt(G.sum(classic.cost), 0)}</div><div class="s">hành vi điển hình của con người</div></div>
      </div>
      <h3 style="margin-top:18px">Đơn đặt hàng của từng khâu so với nhu cầu khách cuối</h3><div id="r1"></div>
      <h3>Tồn kho ròng (tồn − nợ đơn)</h3><div id="r2"></div>
      <div class="g-scroll" style="margin-top:12px"><table class="g-table"><thead><tr><th>Khâu</th><th class="r">Chi phí</th><th class="r">Tỷ lệ Bullwhip</th><th class="r">Đơn lớn nhất</th></tr></thead><tbody>${me.rows}</tbody></table></div>
      <p class="g-note">Tỷ lệ Bullwhip = phương sai đơn đặt của khâu ÷ phương sai nhu cầu khách cuối. Tỷ lệ tăng dần lên phía nhà máy là dấu hiệu của hiệu ứng roi da.</p>
      <div class="g-msg">${verdict(me.total, G.sum(bench.cost), G.sum(classic.cost))}</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="r-again">Chơi lại</button><button class="btn" id="r-setup">Đổi vai / chế độ</button></div>
    </div>
    <div class="game-panel"><h3>Câu hỏi thảo luận</h3><ol class="small" style="margin:0;padding-left:1.2em">
      <li>Nhu cầu khách chỉ tăng một lần từ 4 lên 8. Vì sao đơn của nhà máy dao động mạnh như vậy?</li>
      <li>Bạn có tính đến hàng <em>đã đặt nhưng chưa về</em> khi quyết định không? Điều gì xảy ra khi quên nó?</li>
      <li>Chế độ chia sẻ dữ liệu bán ra giảm chi phí bao nhiêu? Ở MBF, dữ liệu nào tương đương (DMS, POS của chuỗi MT)?</li>
      <li>Nối với bốn nguyên nhân của Lee et al. (1997) — Lecture Notes mục 1.5 và tình huống P&amp;G, Barilla ở Chương 20.</li></ol></div>`;
    G.lineChart(G.$("#r1"), { labels: me.lab, height: 270, series: [{ name: "Khách cuối", data: dem, color: "ink", width: 2.6 }].concat(ROLES.map((r, k) => ({ name: r + (k === cfg.role ? " (bạn)" : ""), data: st.hist.orders[k], color: COLORS[k], width: k === cfg.role ? 2.6 : 1.8 }))), aria: "Đơn đặt hàng các khâu" });
    G.lineChart(G.$("#r2"), { labels: me.lab, height: 240, refLines: [{ y: 0 }], series: ROLES.map((r, k) => ({ name: r, data: st.hist.inv[k].map((v, j) => v - st.hist.back[k][j]), color: COLORS[k], width: k === cfg.role ? 2.6 : 1.6 })), aria: "Tồn kho ròng" });
    G.$("#r-again").addEventListener("click", start);
    G.$("#r-setup").addEventListener("click", setup);
  }

  function verdict(me, share, classic) {
    if (me <= share * 1.1) return "<strong>Xuất sắc!</strong> Chuỗi của bạn gần bằng phương án chia sẻ dữ liệu. Bạn đã tính đến hàng đang về và không phản ứng thái quá.";
    if (me <= classic) return `<strong>Tốt hơn hành vi điển hình.</strong> Nhưng vẫn cao hơn phương án chia sẻ dữ liệu ${G.pct(me / share - 1, 0)} — thử chơi lại ở chế độ chia sẻ để cảm nhận khác biệt.`;
    return `<strong>Bullwhip đã xuất hiện.</strong> Chi phí cả chuỗi cao hơn phương án chia sẻ dữ liệu ${G.pct(me / share - 1, 0)}. Xem biểu đồ: khi thiếu hàng bạn có đặt dồn rồi bị ngập hàng vài tuần sau không?`;
  }

  function autoDemo() {
    const weeks = cfg.weeks, dem = demandSeries(weeks, cfg.demand, G.seed());
    const a = simulateAll(weeks, dem, false), b = simulateAll(weeks, dem, true);
    const lab = dem.map((_, k) => "T" + (k + 1));
    root.innerHTML = `
    <div class="game-panel"><h3>Máy tự chơi: cùng nhu cầu, hai cách vận hành</h3>
      <div class="tiles"><div class="tile bad"><div class="k">Cổ điển · chi phí</div><div class="v">${G.fmt(G.sum(a.cost), 0)}</div><div class="s">Bullwhip nhà máy ${G.fmt(bwRatio(a.hist.orders[3], dem), 1)}×</div></div>
      <div class="tile good"><div class="k">Chia sẻ dữ liệu · chi phí</div><div class="v">${G.fmt(G.sum(b.cost), 0)}</div><div class="s">Bullwhip nhà máy ${G.fmt(bwRatio(b.hist.orders[3], dem), 1)}×</div></div>
      <div class="tile"><div class="k">Tiết kiệm</div><div class="v">${G.pct(1 - G.sum(b.cost) / G.sum(a.cost), 0)}</div></div></div>
      <h3 style="margin-top:16px">Cổ điển — mỗi khâu chỉ thấy đơn của khâu sau</h3><div id="d1"></div>
      <h3>Chia sẻ dữ liệu bán ra — mọi khâu thấy nhu cầu khách cuối và tính đủ hàng đang về</h3><div id="d2"></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="d-play">Tự mình chơi</button><button class="btn" id="d-again">Chạy lại với nhu cầu mới</button></div></div>`;
    const ser = (s) => [{ name: "Khách cuối", data: dem, color: "ink", width: 2.6 }].concat(ROLES.map((r, k) => ({ name: r, data: s.hist.orders[k], color: COLORS[k] })));
    const mx = Math.max(...a.hist.orders.flat(), ...b.hist.orders.flat(), ...dem);
    G.lineChart(G.$("#d1"), { labels: lab, height: 250, yMin: 0, yMax: mx, series: ser(a), aria: "Cổ điển" });
    G.lineChart(G.$("#d2"), { labels: lab, height: 250, yMin: 0, yMax: mx, series: ser(b), aria: "Chia sẻ dữ liệu" });
    G.$("#d-play").addEventListener("click", setup);
    G.$("#d-again").addEventListener("click", autoDemo);
  }

  window.__beer = { simulateAll, demandSeries, bwRatio }; // dùng cho kiểm thử
  setup();
})();
