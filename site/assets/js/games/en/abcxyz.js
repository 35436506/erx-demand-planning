/* ERX · Thử thách ABC × XYZ — phân nhóm 23 mã MBF và chọn chính sách cho từng ô */
(function () {
  "use strict";
  const G = window.G, root = document.getElementById("game"), P = (window.GAME_DATA || {}).portfolio || [];
  if (!root) return;
  let ans1 = {}, ans2 = {}, ans3 = {}, score = [0, 0, 0], showCum = false;
  const XSET = (() => { // 10 mã cho vòng XYZ: ưu tiên mã bị xếp khác nhau giữa Raw CV và CV khử mùa vụ
    const diff = P.filter((p) => p.xyz_raw !== p.xyz); const same = P.filter((p) => p.xyz_raw === p.xyz);
    return diff.concat(same.filter((_, i) => i % 2 === 0)).slice(0, 10);
  })();
  const Q3 = [
    { q: "Cell AX (high value, stable demand) — the most suitable approach?", o: ["The planner reviews every item weekly and adjusts by feel", "Automated statistical forecast, review by exception (Tracking Signal)", "No forecast, make to order", "Use Croston"], a: 1,
      w: "AX holds most of the value but is easy to forecast: automating this group well frees up time for exceptions." },
    { q: "Cell AY (high value, moderate variability) — where the planner should spend the most time because…", o: ["Statistics combined with business information and reviewed at the monthly Demand Review", "Naive is enough", "Set an 85% service level to cut inventory", "Switch to make to order"], a: 0,
      w: "High value plus promotion/event information — where human FVA can be positive." },
    { q: "Cell CZ (low value, highly variable/intermittent like H02, H03) — a sensible policy?", o: ["Multiplicative Holt-Winters, reviewed weekly", "Croston/SBA or make to order, minimal stock, quarterly review; consider delisting", "A 99% service level", "Put all the planner's time into this group"], a: 1,
      w: "Low value, hard to forecast: don't let this group eat your time; use intermittent-demand methods or MTO." },
    { q: "B01 (a summer drink) has a high raw CV but a low deseasonalised CV. XYZ should be classified by…", o: ["Raw CV — variability is variability", "Deseasonalised CV — because seasonality is the forecastable part", "Seasonal items don't need XYZ", "Sales' gut feeling"], a: 1,
      w: "Seasonality is forecastable information; using raw CV wrongly puts seasonal items in the group 'hard'." },
    { q: "Target service levels should differ between cells because…", o: ["To be fair between planners", "Inventory capital should go where value and shortage costs are high; 99% for every item piles capital into group C", "The software requires it", "They shouldn't differ"], a: 1,
      w: "Segmented service levels are a trade-off between shortage cost and inventory capital (Chapters 9, 18)." },
  ];

  function step1() {
    let cum = 0; const tot = G.sum(P.map((p) => p.value));
    const rows = P.map((p) => { const share = p.value / tot; const before = cum; cum += share;
      return `<tr data-i="${p.item}"><td><strong>${p.item}</strong></td><td>${G.esc(p.name)}</td><td class="r">${G.fmt(p.value)}</td><td class="r">${G.pct(share)}</td><td class="r cum" style="${showCum ? "" : "display:none"}">${G.pct(before)} → ${G.pct(cum)}</td>
      <td><div class="mini-seg" data-k="${p.item}">${["A", "B", "C"].map((x) => `<button type="button" data-v="${x}" class="${ans1[p.item] === x ? "on" : ""}">${x}</button>`).join("")}</div></td></tr>`; }).join("");
    root.innerHTML = `<div class="game-panel"><h3>Round 1/3 · Classify ABC by 12-month value</h3>
      <p class="small">Course rule: sort by value, descending; <strong>A</strong> = the items making up the first 80% of cumulative value, <strong>B</strong> = up to 95%, the rest are <strong>C</strong>. An item whose cumulative share <em>before it</em> is below 80% belongs to A.</p>
      <div class="g-row" style="margin-bottom:10px"><label class="small"><input type="checkbox" id="a-cum" ${showCum ? "checked" : ""}> Show the cumulative column (help)</label></div>
      <div class="g-scroll"><table class="g-table"><thead><tr><th>Code</th><th>Name</th><th class="r">Value (VND m)</th><th class="r">Share</th><th class="r cum" style="${showCum ? "" : "display:none"}">Cumulative</th><th>Group</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="a-check">Check round 1</button><span class="small muted" id="a-left"></span></div><div id="a-fb"></div></div>`;
    bindSeg(ans1, () => left());
    G.$("#a-cum").addEventListener("change", (e) => { showCum = e.target.checked; G.$$(".cum").forEach((c) => (c.style.display = showCum ? "" : "none")); });
    const left = () => { const n = P.length - Object.keys(ans1).length; G.$("#a-left").textContent = n ? `Left to sort: ${n} items` : "All sorted"; };
    left();
    G.$("#a-check").addEventListener("click", () => {
      if (Object.keys(ans1).length < P.length) { G.$("#a-fb").innerHTML = '<div class="g-msg no">Sort all 23 items before checking.</div>'; return; }
      let ok = 0;
      P.forEach((p) => { const r = ans1[p.item] === p.abc; ok += r; const tr = G.$(`tr[data-i="${p.item}"]`); tr.className = r ? "ok" : "no";
        G.$$(`.mini-seg[data-k="${p.item}"] button`).forEach((b) => { b.disabled = true; b.className = b.dataset.v === p.abc ? "right" : (b.dataset.v === ans1[p.item] ? "wrong" : ""); }); });
      score[0] = ok; showCum = true; G.$$(".cum").forEach((c) => (c.style.display = ""));
      const nA = P.filter((p) => p.abc === "A").length, nB = P.filter((p) => p.abc === "B").length;
      G.$("#a-fb").innerHTML = `<div class="g-msg ${ok >= 20 ? "ok" : "no"}"><strong>${ok}/${P.length} correct.</strong> Answer: ${nA} A items, ${nB} B items, ${P.length - nA - nB} C items. Only ${nA} A items already make up about 80% of the value — that is where time and high service levels are worth investing.</div><div class="g-row" style="margin-top:10px"><button class="btn primary" id="a-next">On to round 2</button></div>`;
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
    root.innerHTML = `<div class="game-panel"><h3>Round 2/3 · Classify XYZ by variability</h3>
      <p class="small">Course thresholds (monthly data): <strong>X</strong> ≤ 0.15 · <strong>Y</strong> 0.15–0.35 · <strong>Z</strong> &gt; 0.35. Careful: use the right kind of CV!</p>
      <div class="g-scroll"><table class="g-table"><thead><tr><th>Code</th><th>Name</th><th class="r">Raw CV</th><th class="r">Deseasonalised CV</th><th>Group</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="x-check">Check round 2</button></div><div id="x-fb"></div></div>`;
    bindSeg(ans2);
    G.$("#x-check").addEventListener("click", () => {
      if (Object.keys(ans2).length < XSET.length) { G.$("#x-fb").innerHTML = '<div class="g-msg no">Sort all 10 items.</div>'; return; }
      let ok = 0, trap = 0;
      XSET.forEach((p) => { const r = ans2[p.item] === p.xyz; ok += r; if (!r && ans2[p.item] === p.xyz_raw) trap += 1;
        const tr = G.$(`tr[data-i="${p.item}"]`); tr.className = r ? "ok" : "no";
        G.$$(`.mini-seg[data-k="${p.item}"] button`).forEach((b) => { b.disabled = true; b.className = b.dataset.v === p.xyz ? "right" : (b.dataset.v === ans2[p.item] ? "wrong" : ""); });
        G.$(".why", tr).textContent = p.xyz_raw !== p.xyz ? `Raw CV gives ${p.xyz_raw}, but the seasonality is forecastable → ${p.xyz}` : ""; });
      score[1] = ok; G.$("#x-check").disabled = true;
      G.$("#x-fb").innerHTML = `<div class="g-msg ${ok >= 8 ? "ok" : "no"}"><strong>${ok}/10 correct.</strong> ${trap ? `You fell into the raw-CV trap on ${trap} items — seasonal items were wrongly put in the “hard” group.` : "You avoided the raw-CV trap."} XYZ should be measured on the deseasonalised series (or on the forecast error).</div><div class="g-row" style="margin-top:10px"><button class="btn primary" id="x-next">On to round 3</button></div>`;
      G.$("#x-next").addEventListener("click", step3);
    });
  }

  function step3() {
    root.innerHTML = `<div class="game-panel"><h3>Round 3/3 · A policy for each cell</h3><div id="q-list"></div>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="q-done" disabled>See the summary</button></div></div>`;
    const host = G.$("#q-list");
    Q3.forEach((q, k) => {
      const box = G.el("div", { class: "game-panel", style: "box-shadow:none;margin-bottom:10px" }, `<div style="font-weight:600;margin-bottom:8px">${k + 1}. ${G.esc(q.q)}</div><div class="opt-list">${q.o.map((o, j) => `<button type="button" data-j="${j}">${G.esc(o)}</button>`).join("")}</div><div class="fb"></div>`);
      host.appendChild(box);
      G.$$("button", box).forEach((b) => b.addEventListener("click", () => {
        const j = +b.dataset.j; ans3[k] = j;
        G.$$("button", box).forEach((x) => { x.disabled = true; if (+x.dataset.j === q.a) x.classList.add("right"); else if (x === b) x.classList.add("wrong"); });
        G.$(".fb", box).innerHTML = `<div class="g-msg ${j === q.a ? "ok" : "no"}">${j === q.a ? "<strong>Correct.</strong> " : "<strong>Not quite.</strong> "}${G.esc(q.w)}</div>`;
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
    root.innerHTML = `<div class="game-panel"><h3>Summary</h3><div class="tiles">
      <div class="tile"><div class="k">ABC</div><div class="v">${score[0]}/${P.length}</div></div><div class="tile"><div class="k">XYZ</div><div class="v">${score[1]}/10</div></div>
      <div class="tile"><div class="k">Policy</div><div class="v">${score[2]}/${Q3.length}</div></div><div class="tile ${pctv >= 80 ? "good" : ""}"><div class="k">Total</div><div class="v">${pctv}%</div><div class="s">${rec ? "new record" : "record: " + G.store.get("abcxyz").v + "%"}</div></div></div>
      <h3 style="margin-top:16px">MBF's ABC × XYZ matrix (deseasonalised CV)</h3>
      <div class="g-scroll"><table class="g-table"><thead><tr><th></th><th>X · stable</th><th>Y · moderately variable</th><th>Z · highly variable</th></tr></thead><tbody>${mat}</tbody></table></div>
      <p class="g-note">Compare with the Session 7 slides and Lecture Notes section 7.2 — the suggested policy for each cell.</p>
      <div class="g-row" style="margin-top:12px"><button class="btn primary" id="z-again">Play again</button><a class="btn" href="buoi-07.html">Back to Session 7</a></div></div>`;
    G.$("#z-again").addEventListener("click", () => { ans1 = {}; ans2 = {}; ans3 = {}; score = [0, 0, 0]; showCum = false; step1(); });
  }

  if (!P.length) { root.innerHTML = '<p class="muted">Could not load the game data.</p>'; return; }
  step1();
})();
