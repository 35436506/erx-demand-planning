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
      <div class="game-panel"><h3>Thiết lập chính sách</h3>
        <div class="g-row"><span class="g-label" style="width:110px">Chính sách</span><div id="i-pol"></div></div>
        <div class="g-row" id="i-par"></div>
        <div class="g-row"><span class="g-label" style="width:110px">Lead time</span><div id="i-lt"></div></div>
        <div class="g-row" style="margin-top:14px"><button class="btn primary" id="i-run">Chạy mô phỏng 52 tuần <span class="kbd">Enter</span></button><button class="btn sm" id="i-new">Nhu cầu mới</button></div>
        <p class="g-note">Nhu cầu tuần ~ Chuẩn(${MU}; ${SIG}) thùng. Chi phí (nghìn đồng): tồn kho ${H}/thùng/tuần · đặt hàng ${G.fmt(K)}/lần · mất bán ${P}/thùng. Tồn đầu kỳ ${G.fmt(INIT)} thùng. Mục tiêu: <strong>fill rate ≥ ${G.pct(TARGET, 0)}</strong> với tổng chi phí thấp nhất.</p></div>
      <div class="game-panel" id="i-out">${res ? "" : '<p class="muted">Chọn tham số rồi bấm chạy. Mỗi lần thử được ghi vào bảng bên dưới.</p>'}</div>
      <div class="game-panel"><h3>Các lần thử</h3><div id="i-tries"></div></div>
    </div><aside class="game-side"><div class="game-panel"><div class="g-label">Gợi ý lý thuyết (Chương 9, 18)</div>
      <ul class="small" style="padding-left:1.1em;margin:8px 0 0">
      <li>EOQ = √(2·D·K/h) = √(2·${MU}·${G.fmt(K)}/${H}) ≈ <strong>${G.fmt(th.eoq)}</strong></li>
      <li>(s, Q): s = μL + zσ√L. Với L = 2: z = ${G.fmt(th.z95, 2)} → s ≈ ${G.fmt(th.s95)}; z = ${G.fmt(th.z98, 2)} → s ≈ ${G.fmt(th.s98)}</li>
      <li>(R, S): S = μ(R + L) + zσ√(R + L). R = 2 → S ≈ ${G.fmt(th.S2)}</li>
      <li>Lưu ý: z ở trên là mức phục vụ <em>chu kỳ</em> (α); fill rate (β) thường cao hơn α với cùng tồn an toàn.</li></ul>
      <div id="i-best" style="margin-top:12px"></div></div></aside></div>`;
    G.seg(G.$("#i-pol"), [["sQ", "(s, Q) · liên tục"], ["RS", "(R, S) · định kỳ"]], policy, (v) => { policy = v; params(); });
    G.seg(G.$("#i-lt"), [[false, "Cố định 2 tuần"], [true, "Dao động 1–3 tuần"]], ltVar, (v) => { ltVar = v; });
    params();
    G.$("#i-run").addEventListener("click", run);
    G.$("#i-new").addEventListener("click", () => { seed = G.seed() % 100000; tries = []; render(); });
    triesTable(); bestBox();
    if (res) out(res);
  }

  function params() {
    const box = G.$("#i-par");
    box.innerHTML = policy === "sQ"
      ? `<span class="g-label" style="width:110px">Tham số</span><label class="small">Điểm đặt hàng s <input class="g-input" id="p-s" type="number" step="50" min="0" value="${par.s}"></label><label class="small">Lượng đặt Q <input class="g-input" id="p-Q" type="number" step="50" min="50" value="${par.Q}"></label>`
      : `<span class="g-label" style="width:110px">Tham số</span><label class="small">Chu kỳ R (tuần) <input class="g-input" id="p-R" type="number" step="1" min="1" max="8" value="${par.R}"></label><label class="small">Mức tối đa S <input class="g-input" id="p-S" type="number" step="50" min="0" value="${par.S}"></label>`;
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
    G.$("#i-out").innerHTML = `<h3>Kết quả lần thử ${tries.length}</h3><div class="tiles">
      <div class="tile ${ok ? "good" : "bad"}"><div class="k">Fill rate (β)</div><div class="v">${G.pct(res.fill)}</div><div class="s">mục tiêu ≥ ${G.pct(TARGET, 0)}</div></div>
      <div class="tile"><div class="k">Tuần không thiếu (α)</div><div class="v">${G.pct(res.cycle, 0)}</div></div>
      <div class="tile"><div class="k">Tồn bình quân</div><div class="v">${G.fmt(res.avgOn)}</div><div class="s">thùng</div></div>
      <div class="tile"><div class="k">Số lần đặt</div><div class="v">${res.orders}</div></div>
      <div class="tile ${ok ? "good" : ""}"><div class="k">Tổng chi phí</div><div class="v">${G.fmt(res.cost.total / 1000, 1)}</div><div class="s">triệu đồng</div></div></div>
      <p class="small" style="margin-top:8px">Chi phí: tồn kho ${G.fmt(res.cost.hold / 1000, 1)} tr · đặt hàng ${G.fmt(res.cost.order / 1000, 1)} tr · mất bán ${G.fmt(res.cost.lost / 1000, 1)} tr (${G.fmt(res.lostQ)} thùng).</p>
      <div id="i-chart"></div>
      <div class="g-msg ${ok ? "ok" : "no"}">${ok ? "Đạt mục tiêu phục vụ. Thử giảm tồn kho (s hoặc S thấp hơn, hoặc Q gần EOQ) để hạ chi phí mà vẫn giữ ≥ 98%." : "Chưa đạt 98%: tăng điểm đặt hàng s (hoặc S) để che biến động trong lead time. Bật lead time dao động để thấy cần thêm bao nhiêu tồn an toàn."}</div>`;
    const lab = res.D.map((_, i) => "T" + (i + 1));
    G.lineChart(G.$("#i-chart"), { labels: lab, height: 250, yMin: 0, xEvery: 4, series: [
      { name: "Tồn kho thực có", data: res.hOn, color: "green", step: true }, { name: "Vị thế tồn kho (tồn + đang về)", data: res.hIP, color: "blue", dash: true, width: 1.5, step: true },
      { name: "Nhu cầu", data: res.D, color: "muted", width: 1.2 }, { name: "Mất bán", data: res.hLost.map((v) => v > 0 ? v : null), color: "red", dots: true, width: 0 }], aria: "Diễn biến tồn kho" });
  }

  function triesTable() {
    if (!tries.length) { G.$("#i-tries").innerHTML = '<p class="small muted">Chưa có lần thử nào.</p>'; return; }
    const best = tries.filter((x) => x.res.fill >= TARGET && !x.lt).reduce((m, x) => (!m || x.res.cost.total < m.res.cost.total ? x : m), null);
    G.$("#i-tries").innerHTML = `<div class="g-scroll"><table class="g-table"><thead><tr><th>#</th><th>Chính sách</th><th>Lead time</th><th class="r">Fill rate</th><th class="r">Tồn BQ</th><th class="r">Chi phí (tr.đ)</th></tr></thead><tbody>${tries.map((x, k) => `<tr class="${x === best ? "ok me" : x.res.fill < TARGET ? "no" : ""}"><td>${k + 1}</td><td>${x.pol === "sQ" ? "(s, Q)" : "(R, S)"} · ${x.lab}</td><td>${x.lt ? "1–3 tuần" : "2 tuần"}</td><td class="r">${G.pct(x.res.fill)}</td><td class="r">${G.fmt(x.res.avgOn)}</td><td class="r">${G.fmt(x.res.cost.total / 1000, 1)}</td></tr>`).join("")}</tbody></table></div>
      <p class="g-note">Dòng xanh đậm = phương án rẻ nhất đạt mục tiêu (lead time cố định). Bộ nhu cầu #${seed} — đổi “Nhu cầu mới” để thử lại.</p>`;
  }
  function bestBox() {
    const b = G.store.get("inv_" + seed);
    G.$("#i-best").innerHTML = `<div class="g-label">Kỷ lục của bạn (bộ nhu cầu #${seed})</div><div class="stat" style="font-size:1.5rem">${b ? G.fmt(b.v / 1000, 1) + " tr" : "–"}</div><div class="small muted">chi phí thấp nhất đạt fill rate ≥ 98%</div>`;
  }

  document.addEventListener("keydown", (e) => { if (e.key === "Enter" && document.activeElement && document.activeElement.tagName === "BODY") run(); });
  window.__inv = { simulate };
  render();
})();
