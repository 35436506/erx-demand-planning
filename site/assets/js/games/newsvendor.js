/* ERX · Newsvendor — sản xuất hộp quà Tết một lần cho cả mùa: bao nhiêu là vừa? */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const ROUNDS = 8;
  const PRODUCTS = ["Hộp quà Tết Phúc Lộc", "Giỏ quà Tết An Khang", "Hộp bánh Xuân Sum Vầy", "Set gia vị Tết Đoàn Viên", "Hộp quà Tết cao cấp Hưng Thịnh",
    "Hộp kẹo Tết Như Ý", "Combo nước giải khát Tết", "Hộp quà doanh nghiệp Vạn Phúc"];
  let seed, round, rounds, plays, total, totalOpt;

  function makeRound(r, k) {
    const mu = Math.round((2000 + r() * 3000) / 50) * 50, cv = 0.2 + r() * 0.2, sigma = Math.round((mu * cv) / 10) * 10;
    const price = Math.round((180 + r() * 220) / 5) * 5, cost = Math.round((price * (0.35 + r() * 0.35)) / 5) * 5, salvage = Math.round((cost * (0.1 + r() * 0.6)) / 5) * 5;
    const cu = price - cost, co = cost - salvage, cr = cu / (cu + co);
    const D = Math.max(0, Math.round(mu + G.normal(r) * sigma));
    return { name: PRODUCTS[k % PRODUCTS.length], mu, sigma, price, cost, salvage, cu, co, cr, D, qstar: Math.max(0, Math.round(mu + G.normInv(cr) * sigma)) };
  }
  const profit = (x, Q) => x.price * Math.min(Q, x.D) + x.salvage * Math.max(Q - x.D, 0) - x.cost * Q;
  function expProfit(x, Q) { // lợi nhuận kỳ vọng với nhu cầu chuẩn
    const z = (Q - x.mu) / x.sigma, expShort = x.sigma * G.loss(z), expSales = x.mu - expShort, expLeft = Q - expSales;
    return x.price * expSales + x.salvage * expLeft - x.cost * Q;
  }

  function setup() {
    root.innerHTML = `<div class="game-panel"><h3>Bài toán Newsvendor · sản xuất hàng Tết</h3>
      <p>Bạn phụ trách ${ROUNDS} sản phẩm quà Tết. Mỗi sản phẩm chỉ được sản xuất <strong>một lần</strong> trước mùa. Thiếu hàng: mất lãi gộp. Dư hàng: phải thanh lý dưới giá vốn sau Tết. Bạn có dự báo nhu cầu (trung bình và độ lệch chuẩn) — hãy chọn số lượng sản xuất.</p>
      <div class="g-row"><button class="btn primary" id="n-start">Bắt đầu</button></div>
      <p class="g-note">Kỷ lục: ${(() => { const b = G.store.get("nv_ratio"); return b ? G.fmt(b.v, 1) + "% lợi nhuận so với chiến lược tối ưu" : "–"; })()}</p></div>
      <div class="game-panel"><h3>Kiến thức cần nhớ (Lecture Notes Chương 11)</h3><ul class="small" style="margin:0;padding-left:1.1em">
      <li>Chi phí thiếu một thùng: c<sub>u</sub> = giá bán − giá vốn. Chi phí dư một thùng: c<sub>o</sub> = giá vốn − giá thanh lý.</li>
      <li>Tỷ lệ tới hạn CR = c<sub>u</sub> / (c<sub>u</sub> + c<sub>o</sub>). Lượng tối ưu Q* là phân vị CR của phân phối nhu cầu: Q* = μ + z<sub>CR</sub>·σ.</li>
      <li>CR &gt; 50% → làm nhiều hơn trung bình; CR &lt; 50% → làm ít hơn trung bình.</li></ul></div>`;
    G.$("#n-start").addEventListener("click", () => { seed = G.seed(); const r = G.rng(seed); rounds = Array.from({ length: ROUNDS }, (_, k) => makeRound(r, k)); round = 0; plays = []; total = 0; totalOpt = 0; render(); });
  }

  function render(last) {
    const x = rounds[round];
    root.innerHTML = `<div class="game-wrap"><div>
      <div class="game-panel"><div class="g-row" style="justify-content:space-between"><h3 style="margin:0">${round + 1}/${ROUNDS} · ${G.esc(x.name)}</h3><div class="progress-dots">${Array.from({ length: ROUNDS }, (_, k) => `<i class="${k < plays.length ? (plays[k].eff >= 0.97 ? "ok" : "no") : k === round ? "cur" : ""}"></i>`).join("")}</div></div>
        <div class="tiles" style="margin-top:12px">
          <div class="tile"><div class="k">Dự báo nhu cầu</div><div class="v">${G.fmt(x.mu)}</div><div class="s">± ${G.fmt(x.sigma)} (1 độ lệch chuẩn)</div></div>
          <div class="tile"><div class="k">Giá bán</div><div class="v">${G.fmt(x.price)}</div><div class="s">nghìn đ/hộp</div></div>
          <div class="tile"><div class="k">Giá vốn</div><div class="v">${G.fmt(x.cost)}</div><div class="s">nghìn đ/hộp</div></div>
          <div class="tile"><div class="k">Thanh lý sau Tết</div><div class="v">${G.fmt(x.salvage)}</div><div class="s">nghìn đ/hộp</div></div></div>
        <div class="g-row" style="margin-top:14px"><label class="g-label" for="n-q">Số hộp sản xuất</label><input class="g-input" id="n-q" type="number" min="0" step="50" value="${x.mu}" inputmode="numeric">
          <button class="btn primary" id="n-go">Chốt sản xuất <span class="kbd">Enter</span></button><button class="btn sm" id="n-help">Tính giúp chi phí thiếu / dư</button></div>
        <div id="n-helpbox"></div>${last ? lastHtml(last) : ""}</div>
      ${last ? '<div class="game-panel"><h3>Lợi nhuận kỳ vọng theo số lượng sản xuất (sản phẩm vừa rồi)</h3><div id="n-curve"></div></div>' : ""}
    </div><aside class="game-side"><div class="game-panel"><div class="g-label">Lợi nhuận tích lũy</div><div class="stat">${G.fmt(total / 1000, 1)} tr</div>
      <div class="small muted">Chiến lược Q* (cùng nhu cầu thực tế): ${G.fmt(totalOpt / 1000, 1)} tr</div></div></aside></div>`;
    const q = G.$("#n-q"); q.focus(); q.select();
    const go = () => { const v = parseInt(q.value, 10); if (!(v >= 0)) { q.focus(); return; } submit(v); };
    G.$("#n-go").addEventListener("click", go);
    q.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    G.$("#n-help").addEventListener("click", () => {
      G.$("#n-helpbox").innerHTML = `<div class="g-msg">c<sub>u</sub> = ${G.fmt(x.price)} − ${G.fmt(x.cost)} = <strong>${G.fmt(x.cu)}</strong> · c<sub>o</sub> = ${G.fmt(x.cost)} − ${G.fmt(x.salvage)} = <strong>${G.fmt(x.co)}</strong> → CR = <strong>${G.pct(x.cr, 0)}</strong>. ${x.cr > 0.5 ? "CR > 50%: nên làm nhiều hơn dự báo trung bình." : "CR < 50%: nên làm ít hơn dự báo trung bình."} (Phần tính Q* để bạn tự làm: z của CR tra bảng chuẩn hoặc =NORM.S.INV(CR) trong Excel.)</div>`;
    });
    if (last) drawCurve(last);
  }

  function lastHtml(p) {
    const x = p.x;
    return `<div class="g-msg ${p.eff >= 0.97 ? "ok" : "no"}" style="margin-top:14px"><strong>${G.esc(x.name)}:</strong> nhu cầu thực tế <strong>${G.fmt(x.D)}</strong>. Bạn làm ${G.fmt(p.Q)} → lợi nhuận <strong>${G.fmt(p.prof / 1000, 1)} tr</strong>. Q* = ${G.fmt(x.qstar)} (CR ${G.pct(x.cr, 0)}) → ${G.fmt(p.profOpt / 1000, 1)} tr.
      Lợi nhuận <em>kỳ vọng</em> của bạn đạt ${G.pct(p.eff, 0)} so với Q* — ${p.eff >= 0.97 ? "quyết định tốt, dù kết quả thực tế còn phụ thuộc may rủi." : "khoảng cách đến từ quyết định, không chỉ do may rủi."}</div>`;
  }

  function drawCurve(p) {
    const x = p.x, lo = Math.max(0, Math.round(x.mu - 3 * x.sigma)), hi = Math.round(x.mu + 3 * x.sigma), step = Math.max(10, Math.round((hi - lo) / 60 / 10) * 10);
    const qs = []; for (let q = lo; q <= hi; q += step) qs.push(q);
    const ep = qs.map((q) => expProfit(x, q) / 1000);
    const near = (v) => qs.reduce((b, q, i) => (Math.abs(q - v) < Math.abs(qs[b] - v) ? i : b), 0);
    const mark = (v) => qs.map((_, i) => (i === near(v) ? ep[i] : null));
    G.lineChart(G.$("#n-curve"), { labels: qs.map((q) => G.fmt(q)), height: 230, xEvery: 10, yFmt: (v) => G.fmt(v, 0), tipFmt: (v) => G.fmt(v, 1) + " tr", series: [
      { name: "Lợi nhuận kỳ vọng (tr đ)", data: ep, color: "blue" }, { name: "Q* tối ưu", data: mark(x.qstar), color: "green", dots: true, width: 0 },
      { name: "Lựa chọn của bạn", data: mark(p.Q), color: "orange", dots: true, width: 0 }], aria: "Lợi nhuận kỳ vọng" });
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
    root.innerHTML = `<div class="game-panel"><h3>Tổng kết mùa Tết</h3><div class="tiles">
      <div class="tile"><div class="k">Lợi nhuận thực tế</div><div class="v">${G.fmt(total / 1000, 1)} tr</div></div>
      <div class="tile"><div class="k">Chiến lược Q*</div><div class="v">${G.fmt(totalOpt / 1000, 1)} tr</div></div>
      <div class="tile ${effAvg >= 0.97 ? "good" : ""}"><div class="k">Chất lượng quyết định</div><div class="v">${G.pct(effAvg, 1)}</div><div class="s">${rec ? "kỷ lục mới" : "kỷ lục: " + G.fmt(G.store.get("nv_ratio").v, 1) + "%"}</div></div></div>
      <div class="g-scroll" style="margin-top:12px"><table class="g-table"><thead><tr><th>Sản phẩm</th><th class="r">CR</th><th class="r">Dự báo μ</th><th class="r">Bạn làm</th><th class="r">Q*</th><th class="r">Thực tế</th><th class="r">Lợi nhuận (tr)</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-msg">“Chất lượng quyết định” so sánh lợi nhuận <em>kỳ vọng</em> của bạn với Q* — loại bỏ yếu tố may rủi của nhu cầu thực tế. ${over ? `Có ${over} sản phẩm bạn đi <strong>ngược hướng</strong> tỷ lệ tới hạn (CR > 50% mà làm ít hơn trung bình, hoặc ngược lại).` : "Bạn luôn đi đúng hướng của tỷ lệ tới hạn."} Nghiên cứu (Schweitzer &amp; Cachon, 2000) cho thấy người ra quyết định thường chọn quá gần trung bình — “kéo về trung tâm”.</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="n-again">Chơi mùa mới</button><a class="btn" href="buoi-09.html">Về Buổi 9</a></div></div>`;
    G.$("#n-again").addEventListener("click", setup);
  }

  setup();
})();
