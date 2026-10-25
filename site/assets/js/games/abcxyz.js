/* ERX · Thử thách ABC × XYZ — phân nhóm 23 mã MBF và chọn chính sách cho từng ô */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game"), P = (window.GAME_DATA || {}).portfolio || [];
  if (!root) return;
  let ans1 = {}, ans2 = {}, ans3 = {}, score = [0, 0, 0], showCum = false;
  const XSET = (() => { // 10 mã cho vòng XYZ: ưu tiên mã bị xếp khác nhau giữa CV thô và CV khử mùa vụ
    const diff = P.filter((p) => p.xyz_raw !== p.xyz); const same = P.filter((p) => p.xyz_raw === p.xyz);
    return diff.concat(same.filter((_, i) => i % 2 === 0)).slice(0, 10);
  })();
  const Q3 = [
    { q: "Ô AX (giá trị cao, nhu cầu ổn định) — cách làm phù hợp nhất?", o: ["Planner rà soát từng mã mỗi tuần, chỉnh tay theo cảm nhận", "Dự báo thống kê tự động, rà soát theo ngoại lệ (Tracking Signal)", "Không dự báo, sản xuất theo đơn", "Dùng Croston"], a: 1,
      w: "AX chiếm phần lớn giá trị nhưng dễ dự báo: tự động hóa tốt nhóm này giải phóng thời gian cho ngoại lệ." },
    { q: "Ô AY (giá trị cao, biến động vừa) — nơi planner nên dành nhiều thời gian nhất vì…", o: ["Thống kê kết hợp thông tin kinh doanh và rà soát tại Demand Review hằng tháng", "Chỉ cần Naive", "Đặt mức phục vụ 85% để giảm tồn kho", "Chuyển sang sản xuất theo đơn"], a: 0,
      w: "Giá trị lớn và có thông tin khuyến mãi/sự kiện — nơi FVA của con người có thể dương." },
    { q: "Ô CZ (giá trị thấp, rất biến động/gián đoạn như H02, H03) — chính sách hợp lý?", o: ["Holt-Winters nhân, rà soát hằng tuần", "Croston/SBA hoặc sản xuất theo đơn, tồn tối thiểu, rà soát hằng quý; xem xét cắt mã", "Mức phục vụ 99%", "Dồn hết thời gian planner vào nhóm này"], a: 1,
      w: "Giá trị thấp, khó dự báo: đừng để nhóm này ngốn thời gian; dùng phương pháp cho nhu cầu gián đoạn hoặc MTO." },
    { q: "B01 (nước giải khát mùa hè) có CV thô cao nhưng CV đã khử mùa vụ thấp. Nên xếp XYZ theo…", o: ["CV thô — vì biến động là biến động", "CV đã khử mùa vụ — vì mùa vụ là phần dự báo được", "Không cần XYZ cho hàng mùa vụ", "Theo cảm nhận của Sales"], a: 1,
      w: "Mùa vụ là thông tin dự báo được; dùng CV thô sẽ xếp nhầm hàng mùa vụ vào nhóm 'khó'." },
    { q: "Mức phục vụ mục tiêu nên khác nhau giữa các ô vì…", o: ["Để công bằng giữa các planner", "Vốn tồn kho nên tập trung vào nơi tạo giá trị và chi phí thiếu hàng cao; đặt 99% cho mọi mã sẽ dồn vốn vào nhóm C", "Phần mềm bắt buộc", "Không nên khác nhau"], a: 1,
      w: "Mức phục vụ theo phân khúc là đánh đổi giữa chi phí thiếu hàng và vốn tồn kho (Chương 9, 18)." },
  ];

  function step1() {
    let cum = 0; const tot = G.sum(P.map((p) => p.value));
    const rows = P.map((p) => { const share = p.value / tot; const before = cum; cum += share;
      return `<tr data-i="${p.item}"><td><strong>${p.item}</strong></td><td>${G.esc(p.name)}</td><td class="r">${G.fmt(p.value)}</td><td class="r">${G.pct(share)}</td><td class="r cum" style="${showCum ? "" : "display:none"}">${G.pct(before)} → ${G.pct(cum)}</td>
      <td><div class="mini-seg" data-k="${p.item}">${["A", "B", "C"].map((x) => `<button type="button" data-v="${x}" class="${ans1[p.item] === x ? "on" : ""}">${x}</button>`).join("")}</div></td></tr>`; }).join("");
    root.innerHTML = `<div class="game-panel"><h3>Vòng 1/3 · Xếp nhóm ABC theo giá trị 12 tháng</h3>
      <p class="small">Quy tắc khóa học: sắp giá trị giảm dần; <strong>A</strong> = các mã tạo 80% giá trị lũy kế đầu tiên, <strong>B</strong> = tới 95%, còn lại là <strong>C</strong>. Mã có lũy kế <em>trước nó</em> dưới 80% thuộc A.</p>
      <div class="g-row" style="margin-bottom:10px"><label class="small"><input type="checkbox" id="a-cum" ${showCum ? "checked" : ""}> Hiện cột lũy kế (trợ giúp)</label></div>
      <div class="g-scroll"><table class="g-table"><thead><tr><th>Mã</th><th>Tên</th><th class="r">Giá trị (tr.đ)</th><th class="r">Tỷ trọng</th><th class="r cum" style="${showCum ? "" : "display:none"}">Lũy kế</th><th>Nhóm</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="a-check">Chấm vòng 1</button><span class="small muted" id="a-left"></span></div><div id="a-fb"></div></div>`;
    bindSeg(ans1, () => left());
    G.$("#a-cum").addEventListener("change", (e) => { showCum = e.target.checked; G.$$(".cum").forEach((c) => (c.style.display = showCum ? "" : "none")); });
    const left = () => { const n = P.length - Object.keys(ans1).length; G.$("#a-left").textContent = n ? `Còn ${n} mã chưa xếp` : "Đã xếp đủ"; };
    left();
    G.$("#a-check").addEventListener("click", () => {
      if (Object.keys(ans1).length < P.length) { G.$("#a-fb").innerHTML = '<div class="g-msg no">Hãy xếp đủ 23 mã trước khi chấm.</div>'; return; }
      let ok = 0;
      P.forEach((p) => { const r = ans1[p.item] === p.abc; ok += r; const tr = G.$(`tr[data-i="${p.item}"]`); tr.className = r ? "ok" : "no";
        G.$$(`.mini-seg[data-k="${p.item}"] button`).forEach((b) => { b.disabled = true; b.className = b.dataset.v === p.abc ? "right" : (b.dataset.v === ans1[p.item] ? "wrong" : ""); }); });
      score[0] = ok; showCum = true; G.$$(".cum").forEach((c) => (c.style.display = ""));
      const nA = P.filter((p) => p.abc === "A").length, nB = P.filter((p) => p.abc === "B").length;
      G.$("#a-fb").innerHTML = `<div class="g-msg ${ok >= 20 ? "ok" : "no"}"><strong>${ok}/${P.length} đúng.</strong> Đáp án: ${nA} mã A, ${nB} mã B, ${P.length - nA - nB} mã C. Chỉ ${nA} mã A đã tạo khoảng 80% giá trị — đó là nơi đáng đầu tư thời gian và mức phục vụ cao.</div><div class="g-row" style="margin-top:10px"><button class="btn primary" id="a-next">Sang vòng 2</button></div>`;
      G.$("#a-check").disabled = true;
      G.$("#a-next").addEventListener("click", step2);
    });
  }

  function bindSeg(store, cb) {
    G.$$(".mini-seg").forEach((seg) => G.$$("button", seg).forEach((b) => b.addEventListener("click", () => {
      if (b.disabled) return; store[seg.dataset.k] = b.dataset.v; G.$$("button", seg).forEach((x) => x.classList.toggle("on", x === b)); cb && cb();
    })));
  }

  function step2() {
    const rows = XSET.map((p) => `<tr data-i="${p.item}"><td><strong>${p.item}</strong></td><td>${G.esc(p.name)}</td><td class="r">${G.fmt(p.cv_raw, 2)}</td><td class="r">${G.fmt(p.cv_adj, 2)}</td>
      <td><div class="mini-seg" data-k="${p.item}">${["X", "Y", "Z"].map((x) => `<button type="button" data-v="${x}">${x}</button>`).join("")}</div></td><td class="small why"></td></tr>`).join("");
    root.innerHTML = `<div class="game-panel"><h3>Vòng 2/3 · Xếp nhóm XYZ theo độ biến động</h3>
      <p class="small">Ngưỡng của khóa học (dữ liệu tháng): <strong>X</strong> ≤ 0,15 · <strong>Y</strong> 0,15–0,35 · <strong>Z</strong> &gt; 0,35. Cẩn thận: dùng đúng loại CV!</p>
      <div class="g-scroll"><table class="g-table"><thead><tr><th>Mã</th><th>Tên</th><th class="r">CV thô</th><th class="r">CV đã khử mùa vụ</th><th>Nhóm</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="x-check">Chấm vòng 2</button></div><div id="x-fb"></div></div>`;
    bindSeg(ans2);
    G.$("#x-check").addEventListener("click", () => {
      if (Object.keys(ans2).length < XSET.length) { G.$("#x-fb").innerHTML = '<div class="g-msg no">Hãy xếp đủ 10 mã.</div>'; return; }
      let ok = 0, trap = 0;
      XSET.forEach((p) => { const r = ans2[p.item] === p.xyz; ok += r; if (!r && ans2[p.item] === p.xyz_raw) trap += 1;
        const tr = G.$(`tr[data-i="${p.item}"]`); tr.className = r ? "ok" : "no";
        G.$$(`.mini-seg[data-k="${p.item}"] button`).forEach((b) => { b.disabled = true; b.className = b.dataset.v === p.xyz ? "right" : (b.dataset.v === ans2[p.item] ? "wrong" : ""); });
        G.$(".why", tr).textContent = p.xyz_raw !== p.xyz ? `CV thô xếp ${p.xyz_raw}, nhưng mùa vụ dự báo được → ${p.xyz}` : ""; });
      score[1] = ok; G.$("#x-check").disabled = true;
      G.$("#x-fb").innerHTML = `<div class="g-msg ${ok >= 8 ? "ok" : "no"}"><strong>${ok}/10 đúng.</strong> ${trap ? `Bạn rơi vào bẫy CV thô ở ${trap} mã — hàng mùa vụ bị xếp nhầm vào nhóm “khó”.` : "Bạn đã tránh được bẫy CV thô."} XYZ nên đo trên chuỗi đã khử mùa vụ (hoặc trên sai số dự báo).</div><div class="g-row" style="margin-top:10px"><button class="btn primary" id="x-next">Sang vòng 3</button></div>`;
      G.$("#x-next").addEventListener("click", step3);
    });
  }

  function step3() {
    root.innerHTML = `<div class="game-panel"><h3>Vòng 3/3 · Chính sách cho từng ô</h3><div id="q-list"></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="q-done" disabled>Xem tổng kết</button></div></div>`;
    const host = G.$("#q-list");
    Q3.forEach((q, k) => {
      const box = G.el("div", { class: "game-panel", style: "box-shadow:none;margin-bottom:10px" }, `<div style="font-weight:600;margin-bottom:8px">${k + 1}. ${G.esc(q.q)}</div><div class="opt-list">${q.o.map((o, j) => `<button type="button" data-j="${j}">${G.esc(o)}</button>`).join("")}</div><div class="fb"></div>`);
      host.appendChild(box);
      G.$$("button", box).forEach((b) => b.addEventListener("click", () => {
        const j = +b.dataset.j; ans3[k] = j;
        G.$$("button", box).forEach((x) => { x.disabled = true; if (+x.dataset.j === q.a) x.classList.add("right"); else if (x === b) x.classList.add("wrong"); });
        G.$(".fb", box).innerHTML = `<div class="g-msg ${j === q.a ? "ok" : "no"}">${j === q.a ? "<strong>Đúng.</strong> " : "<strong>Chưa đúng.</strong> "}${G.esc(q.w)}</div>`;
        if (Object.keys(ans3).length === Q3.length) G.$("#q-done").disabled = false;
      }));
    });
    G.$("#q-done").addEventListener("click", () => { score[2] = Q3.filter((q, k) => ans3[k] === q.a).length; finish(); });
  }

  function finish() {
    const tot = score[0] + score[1] + score[2], max = P.length + XSET.length + Q3.length, pctv = Math.round((tot / max) * 100);
    const rec = G.store.best("abcxyz", pctv, true);
    const cells = {}; P.forEach((p) => { const c = p.abc + p.xyz; cells[c] = (cells[c] || []).concat(p.item); });
    const mat = ["A", "B", "C"].map((a) => `<tr><th>${a}</th>${["X", "Y", "Z"].map((x) => `<td>${(cells[a + x] || []).join(", ") || "—"}</td>`).join("")}</tr>`).join("");
    root.innerHTML = `<div class="game-panel"><h3>Tổng kết</h3><div class="tiles">
      <div class="tile"><div class="k">ABC</div><div class="v">${score[0]}/${P.length}</div></div><div class="tile"><div class="k">XYZ</div><div class="v">${score[1]}/10</div></div>
      <div class="tile"><div class="k">Chính sách</div><div class="v">${score[2]}/${Q3.length}</div></div><div class="tile ${pctv >= 80 ? "good" : ""}"><div class="k">Tổng</div><div class="v">${pctv}%</div><div class="s">${rec ? "kỷ lục mới" : "kỷ lục: " + G.store.get("abcxyz").v + "%"}</div></div></div>
      <h3 style="margin-top:16px">Ma trận ABC × XYZ của MBF (CV đã khử mùa vụ)</h3>
      <div class="g-scroll"><table class="g-table"><thead><tr><th></th><th>X · ổn định</th><th>Y · biến động vừa</th><th>Z · rất biến động</th></tr></thead><tbody>${mat}</tbody></table></div>
      <p class="g-note">So với slide Buổi 7 và Lecture Notes mục 7.2 — chính sách gợi ý cho từng ô.</p>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="z-again">Chơi lại</button><a class="btn" href="buoi-07.html">Về Buổi 7</a></div></div>`;
    G.$("#z-again").addEventListener("click", () => { ans1 = {}; ans2 = {}; ans3 = {}; score = [0, 0, 0]; showCum = false; step1(); });
  }

  if (!P.length) { root.innerHTML = '<p class="muted">Không tải được dữ liệu trò chơi.</p>'; return; }
  step1();
})();
