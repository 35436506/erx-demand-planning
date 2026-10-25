/* ERX · Đoán ô Pegels — nhìn chuỗi, xác định dạng xu hướng × mùa vụ */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game");
  if (!root) return;
  const T = ["N", "A", "M"], S = ["N", "A", "M"];
  const TN = { N: "Không xu hướng", A: "Xu hướng cộng (thẳng)", M: "Xu hướng nhân (cong)" };
  const SN = { N: "Không mùa vụ", A: "Mùa vụ cộng", M: "Mùa vụ nhân" };
  const METHOD = { NN: "SES / Naive", NA: "Seasonal Naive · HW cộng không xu hướng", NM: "HW nhân không xu hướng", AN: "Holt (hoặc Holt tắt dần)", AA: "Holt-Winters cộng",
    AM: "Holt-Winters nhân", MN: "Holt trên log(y) · xu hướng nhân", MA: "Xu hướng nhân + mùa vụ cộng (hiếm)", MM: "Holt-Winters nhân trên log hoặc ETS(M,M,M)" };
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
    return c.tk === "N" && c.sk !== "N" && sk !== "N"; // không có xu hướng: cộng và nhân trông như nhau
  }

  function setup() {
    root.innerHTML = `<div class="game-panel"><h3>Đoán ô Pegels</h3>
      <p>Mỗi vòng bạn thấy 36 tháng của một sản phẩm. Hãy chọn ô đúng trong ma trận Pegels: <strong>xu hướng</strong> (không · cộng = đường thẳng · nhân = đường cong) × <strong>mùa vụ</strong> (không · cộng = biên độ không đổi · nhân = biên độ phình theo mức bán).</p>
      <div class="g-row"><span class="g-label" style="width:90px">Độ khó</span><div id="p-lv"></div></div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="p-start">Bắt đầu ${ROUNDS} vòng</button></div>
      <p class="g-note">Kỷ lục của bạn: ${(() => { const b = G.store.get("pegels_" + "easy"), h = G.store.get("pegels_" + "hard"); return `Dễ ${b ? b.v + "/" + ROUNDS : "–"} · Khó ${h ? h.v + "/" + ROUNDS : "–"}`; })()}</p></div>
      <div class="game-panel"><h3>Bốn câu hỏi khi nhìn một chuỗi</h3><ol class="small" style="margin:0;padding-left:1.2em">
      <li>Mức trung bình từng năm có tăng/giảm không? Tăng đều một <em>lượng</em> → cộng; tăng đều một <em>tỷ lệ %</em> (đường cong dốc dần) → nhân.</li>
      <li>Đỉnh/đáy có lặp lại cùng tháng mỗi năm không? → có mùa vụ.</li>
      <li>Biên độ mùa vụ phình to khi mức bán tăng? → mùa vụ nhân; giữ nguyên → cộng.</li>
      <li>Không có xu hướng thì mùa vụ cộng và nhân trông giống nhau — cả hai đều được tính đúng.</li></ol></div>`;
    G.seg(G.$("#p-lv"), [["easy", "Dễ (ít nhiễu)"], ["hard", "Khó (nhiều nhiễu)"]], level, (v) => (level = v));
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
      <div class="game-panel"><div class="g-row" style="justify-content:space-between"><h3 style="margin:0">Vòng ${round + 1} / ${ROUNDS}</h3><div class="progress-dots">${dots}</div></div>
        <div id="p-chart" style="margin-top:8px"></div>
        <div id="p-fb"></div></div>
      <div class="game-panel"><h3>Chọn ô Pegels</h3>
        <div class="pgrid"><div class="h"></div>${S.map((sk) => `<div class="h">${SN[sk]}</div>`).join("")}${cells}</div>
        <div class="g-row" style="margin-top:12px">${answered ? `<button class="btn primary" id="p-next">${round + 1 >= ROUNDS ? "Xem kết quả" : "Vòng tiếp"} <span class="kbd">Enter</span></button>` : ""}</div></div>
    </div><aside class="game-side"><div class="game-panel"><div class="g-label">Điểm</div><div class="stat">${score}/${ROUNDS}</div>
      <p class="small muted" style="margin-top:8px">Sau khi chọn, đường <strong>nét đứt</strong> cho thấy xu hướng thật và <strong>vùng mờ</strong> cho thấy biên độ mùa vụ.</p></div></aside></div>`;
    const series = [{ name: "Nhu cầu", data: cur.y, color: "blue", width: 2.2 }];
    const bands = [];
    if (answered) { series.push({ name: "Xu hướng thật", data: cur.tr, color: "ink", dash: true, width: 2.2 }); if (cur.sk !== "N") bands.push({ lo: cur.lo, hi: cur.hi, color: "orange", opacity: 0.13 }); }
    G.lineChart(G.$("#p-chart"), { labels: cur.labels, series, bands, height: 270, yMin: 0, xEvery: 6, aria: "Chuỗi nhu cầu cần đoán" });
    if (!answered) G.$$(".pgrid button").forEach((b) => b.addEventListener("click", () => answer(b.dataset.t, b.dataset.s)));
    else {
      const ok = okAnswer(cur, pick[0], pick[1]);
      const why = [];
      why.push(cur.tk === "N" ? "Mức nền đi ngang qua các năm." : cur.tk === "A" ? "Mức nền tăng đều một lượng mỗi tháng — đường xu hướng là <strong>đường thẳng</strong>." : "Mức nền tăng theo tỷ lệ % — đường xu hướng <strong>cong dốc dần</strong>.");
      why.push(cur.sk === "N" ? "Không có đỉnh/đáy lặp lại theo tháng." : cur.sk === "A" ? "Biên độ mùa vụ giữ nguyên dù mức bán thay đổi (dải song song)." : "Biên độ mùa vụ phình to khi mức bán tăng (dải loe rộng).");
      if (cur.tk === "N" && cur.sk !== "N") why.push("Vì không có xu hướng, mùa vụ cộng và nhân trông giống nhau — chọn A hay M đều đúng.");
      G.$("#p-fb").innerHTML = `<div class="g-msg ${ok ? "ok" : "no"}"><strong>${ok ? "Chính xác!" : "Chưa đúng."}</strong> Đáp án: ô <strong>(${cur.tk},${cur.sk})</strong> → ${METHOD[cur.tk + cur.sk]}. ${why.join(" ")}</div>`;
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
    root.innerHTML = `<div class="game-panel"><h3>Hoàn thành!</h3><div class="tiles"><div class="tile ${score >= 8 ? "good" : ""}"><div class="k">Điểm</div><div class="v">${score}/${ROUNDS}</div><div class="s">${rec ? "kỷ lục mới" : "kỷ lục: " + G.store.get("pegels_" + level).v + "/" + ROUNDS}</div></div></div>
      <div class="g-msg ${score >= 8 ? "ok" : ""}">${score >= 8 ? "<strong>Mắt tinh!</strong> Bạn đọc dữ liệu rất tốt." : score >= 5 ? "<strong>Khá tốt.</strong> Lỗi hay gặp: nhầm xu hướng cộng với nhân khi nhiễu lớn, hoặc bỏ sót mùa vụ yếu." : "<strong>Cần luyện thêm.</strong> Hãy nhìn đường mức trung bình từng năm trước, rồi mới nhìn biên độ."} Nhớ rằng ô Pegels chỉ là điểm xuất phát — mô hình cuối cùng luôn được chọn bằng sai số ngoài mẫu (Buổi 3–5).</div>
      <div class="g-row" style="margin-top:14px"><button class="btn primary" id="p-again">Chơi lại</button><a class="btn" href="buoi-05.html">Về Buổi 5</a></div></div>`;
    G.$("#p-again").addEventListener("click", setup);
  }

  document.addEventListener("keydown", (e) => { if (e.key === "Enter") { const b = G.$("#p-next"); if (b && document.activeElement !== b) b.click(); } });
  setup();
})();
