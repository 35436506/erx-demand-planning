/* ERX Demand Planning module: navigation, language switch, schedule, Lab, progress tracking (stored in the browser).
   One script for both languages: the page language comes from <html lang>. */
(function () {
  "use strict";
  const CFG = window.ERX_CONFIG || {};
  const LANG = (document.documentElement.lang || "vi").toLowerCase().startsWith("en") ? "en" : "vi";
  const I18N = {
    vi: {
      locale: "vi-VN", byClass: "Theo lịch lớp", next: "Buổi tiếp theo", session: "Buổi", today: "hôm nay", inDays: (d) => "còn " + d + " ngày",
      prepare: "Chuẩn bị cho buổi học", course: "Khóa học", done: "Đã hoàn thành 10 buổi", doneSub: "Xem lại tài liệu và kế hoạch 30–60–90 ngày ở Buổi 10.",
      labNoCfg: "Lab chưa được cấu hình — xem trang Lab", labOff: "Lab chưa được bật cho website này",
      hw: "Bài tập BT1–BT8", part: "Tham gia & exit ticket", cap: "Capstone cá nhân", pres: "Trình bày S&OP nhóm",
      bands: ["Xuất sắc (Distinction)", "Khá (Merit)", "Đạt (Pass)", "Chưa đạt"], none: "chưa có",
      imported: "Đã nhập tiến độ từ file.", badFile: "File không hợp lệ.", confirm: "Bấm lần nữa để xóa hết", reset: "Xóa tiến độ", cleared: "Đã xóa tiến độ trên trình duyệt này.",
      exportName: "ERX_tien_do_", time: CFG.SESSION_TIME || "",
    },
    en: {
      locale: "en-GB", byClass: "See class schedule", next: "Next session", session: "Session", today: "today", inDays: (d) => "in " + d + (d === 1 ? " day" : " days"),
      prepare: "Prepare for the session", course: "Course", done: "All 10 sessions completed", doneSub: "Review the materials and the 30–60–90 day plan in Session 10.",
      labNoCfg: "The Lab is not configured — see the Lab page", labOff: "The Lab is not enabled for this website",
      hw: "Homework HW1–HW8", part: "Participation & exit tickets", cap: "Individual capstone", pres: "Group S&OP presentation",
      bands: ["Distinction", "Merit", "Pass", "Not yet passed"], none: "none yet",
      imported: "Progress imported from file.", badFile: "Invalid file.", confirm: "Click again to clear everything", reset: "Clear progress", cleared: "Progress cleared in this browser.",
      exportName: "ERX_progress_", time: CFG.SESSION_TIME_EN || (CFG.SESSION_TIME || "").replace("giờ Việt Nam", "Vietnam time"),
    },
  };
  const T = I18N[LANG];
  const KEY = "erx_dpf_progress_v1";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  // ---------- lưu trữ an toàn (có thể bị chặn ở chế độ riêng tư)
  const mem = {};
  const ls = {
    get(k) { try { return window.localStorage.getItem(k); } catch (e) { return mem[k] ?? null; } },
    set(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { mem[k] = v; } },
    del(k) { try { window.localStorage.removeItem(k); } catch (e) { delete mem[k]; } },
  };
  function load() { try { return JSON.parse(ls.get(KEY) || "{}") || {}; } catch (e) { return {}; } }
  let state = load();
  function save() { state._updated = new Date().toISOString(); ls.set(KEY, JSON.stringify(state)); refresh(); }
  function getP(path) { return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), state); }
  function setP(path, v) {
    const ks = path.split("."); let o = state;
    ks.slice(0, -1).forEach((k) => { if (typeof o[k] !== "object" || o[k] === null) o[k] = {}; o = o[k]; });
    if (v === "" || v === null || v === false) delete o[ks[ks.length - 1]]; else o[ks[ks.length - 1]] = v;
    save();
  }

  // ---------- language switch: remember the choice (shared by every ERX module) and keep query/hash
  try { localStorage.setItem("erx.lang", LANG); } catch (e) { /* storage blocked */ }
  $$("[data-lang-switch]").forEach((a) => {
    a.addEventListener("click", () => { try { localStorage.setItem("erx.lang", a.dataset.langSwitch); } catch (e) { /* ignore */ } });
    if (location.search || location.hash) a.href = a.getAttribute("href").split(/[?#]/)[0] + location.search + location.hash;
  });

  // ---------- light/dark theme
  const themeBtn = $("#theme-toggle");
  const savedTheme = ls.get("erx_theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  if (themeBtn) themeBtn.addEventListener("click", () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const nx = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = nx; ls.set("erx_theme", nx);
  });
  const navBtn = $("#nav-toggle");
  if (navBtn) navBtn.addEventListener("click", () => { const n = $("#nav"); n.classList.toggle("open"); navBtn.setAttribute("aria-expanded", n.classList.contains("open")); });

  // ---------- lịch học
  function parseD(s) { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || ""); return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null; }
  function sessionDate(n) {
    if (Array.isArray(CFG.SESSION_DATES) && CFG.SESSION_DATES[n - 1]) return parseD(CFG.SESSION_DATES[n - 1]);
    const s = parseD(CFG.START_DATE); if (!s) return null;
    const d = new Date(s); d.setDate(d.getDate() + 7 * (n - 1)); return d;
  }
  function dueDate(n) { // BT n: 2 ngày trước buổi n+1 (BT9: 48 giờ trước Buổi 10)
    const nx = sessionDate(Math.min(n + 1, 10)); if (!nx) return null;
    const d = new Date(nx); d.setDate(d.getDate() - 2); return d;
  }
  const fmtD = (d, long) => d ? d.toLocaleDateString(T.locale, long ? { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" } : { day: "2-digit", month: "2-digit", year: "numeric" }) : "";
  $$("[data-date]").forEach((el) => { const d = sessionDate(+el.dataset.date); el.textContent = d ? (el.dataset.prefix || "") + fmtD(d, el.dataset.long === "1") : (el.dataset.fallback ?? T.byClass); });
  $$("[data-due]").forEach((el) => { const d = dueDate(+el.dataset.due); el.textContent = d ? "23:59 · " + fmtD(d) : (el.dataset.fallback || el.textContent); });
  $$("[data-cfg]").forEach((el) => { const v = CFG[el.dataset.cfg]; if (v) el.textContent = v; else if (el.dataset.hideEmpty) el.closest(el.dataset.hideEmpty)?.remove(); });
  $$("[data-cfg-href]").forEach((el) => { const v = CFG[el.dataset.cfgHref]; if (v) el.href = v; else el.remove(); });

  const nextBox = $("#next-session");
  if (nextBox) {
    const today = new Date(); today.setHours(0, 0, 0, 0);
    let found = null;
    for (let n = 1; n <= 10; n++) { const d = sessionDate(n); if (d && d >= today) { found = n; break; } }
    const titles = JSON.parse(nextBox.dataset.titles || "[]");
    if (found) {
      const d = sessionDate(found); const days = Math.round((d - today) / 864e5);
      nextBox.innerHTML = `<div class="kicker">${T.next}</div><div class="title" style="font-weight:600;font-size:1.1rem">${T.session} ${found} · ${titles[found - 1] || ""}</div>
        <p class="muted small" style="margin:.3em 0 .8em">${fmtD(d, true)} · ${T.time} · ${days === 0 ? T.today : T.inDays(days)}</p>
        <a class="btn sm primary" href="buoi-${String(found).padStart(2, "0")}.html">${T.prepare}</a>`;
    } else if (sessionDate(1)) {
      nextBox.innerHTML = `<div class="kicker">${T.course}</div><div style="font-weight:600">${T.done}</div><p class="muted small">${T.doneSub}</p>`;
    }
  }

  // ---------- Forecasting Lab
  // LAB_URL set in config.js → use it (Lab deployed as its own service).
  // Otherwise look for the Lab next to the module: <module root>/lab/ (pages live in <module root>/vi|en/).
  let labBase;
  async function labUrl() {
    if (labBase !== undefined) return labBase;
    if (CFG.LAB_URL) { labBase = CFG.LAB_URL.replace(/\/+$/, ""); return labBase; }
    const guess = new URL("../lab", location.href).href;
    try {
      const r = await fetch(guess + "/_stcore/health", { cache: "no-store" });
      labBase = r.ok ? guess : null;
    } catch (e) { labBase = null; }
    return labBase;
  }
  const labLink = (base, page, extra) => base + "/" + (page || "") + "?lang=" + LANG + (extra || "");
  labUrl().then((base) => {
    $$("[data-lab]").forEach((a) => {
      const page = a.dataset.lab;
      if (base) { a.href = labLink(base, page); a.target = "_blank"; a.rel = "noopener"; }
      else { a.href = "lab.html"; a.title = T.labNoCfg; }
    });
    const frame = $("#lab-frame");
    if (frame) {
      const params = new URLSearchParams(location.search);
      if (base) {
        frame.src = labLink(base, params.get("p"), "&embed=true&embed_options=light_theme");
        $("#lab-missing")?.remove();
        $$("[data-lab-switch]").forEach((b) => b.addEventListener("click", () => {
          frame.src = labLink(base, b.dataset.labSwitch, "&embed=true&embed_options=light_theme");
          $$("[data-lab-switch]").forEach((x) => x.classList.remove("primary")); b.classList.add("primary");
        }));
      } else {
        frame.remove(); $(".lab-pages")?.remove();
        const t = $("#lab-missing .t"); if (t) t.textContent = T.labOff;
      }
    }
  });

  // ---------- LMS
  $$("[data-lms]").forEach((a) => { if (CFG.LMS_URL) { a.href = CFG.LMS_URL; a.target = "_blank"; a.rel = "noopener"; } else a.remove(); });

  // ---------- tiến độ: liên kết ô nhập
  function bind() {
    $$("[data-p]").forEach((el) => {
      const p = el.dataset.p; const v = getP(p);
      if (el.type === "checkbox") el.checked = !!v; else el.value = v ?? "";
      if (el._bound) return; el._bound = true;
      el.addEventListener("change", () => {
        if (el.type === "checkbox") setP(p, el.checked);
        else {
          let x = el.value.trim(); if (x === "") { setP(p, ""); return; }
          x = Number(x.replace(",", ".")); const mn = el.min !== "" ? +el.min : -Infinity, mx = el.max !== "" ? +el.max : Infinity;
          if (!isFinite(x)) { el.value = ""; setP(p, ""); return; }
          x = Math.max(mn, Math.min(mx, x)); el.value = x; setP(p, x);
        }
      });
    });
  }
  const ITEMS = (n) => (n <= 9 ? ["att", "slides", "excel", "lab", "hw"] : ["att", "slides", "excel", "lab", "cap"]);
  function sessPct(n) { const s = (state.s || {})[n] || {}; const it = ITEMS(n); return Math.round((100 * it.filter((k) => s[k]).length) / it.length); }
  function overall() { let t = 0; for (let n = 1; n <= 10; n++) t += sessPct(n); return Math.round(t / 10); }
  function grade() {
    const s = state.s || {};
    const hw = []; for (let n = 1; n <= 8; n++) if (s[n] && s[n].hwScore !== undefined) hw.push(+s[n].hwScore);
    const ex = []; for (let n = 1; n <= 9; n++) if (s[n] && s[n].exit !== undefined) ex.push(+s[n].exit);
    ex.sort((a, b) => b - a); const ex8 = ex.slice(0, 8);
    const cap = state.cap && state.cap.score !== undefined ? +state.cap.score : null;
    const pres = state.pres && state.pres.score !== undefined ? +state.pres.score : null;
    const comp = [
      { k: T.hw, w: 30, have: hw.length, of: 8, v: hw.length ? (hw.reduce((a, b) => a + b, 0) / hw.length) / 4 : null, earned: (hw.reduce((a, b) => a + b, 0) / 4 / 8) * 30 },
      { k: T.part, w: 10, have: ex8.length, of: 8, v: ex8.length ? (ex8.reduce((a, b) => a + b, 0) / ex8.length) / 5 : null, earned: (ex8.reduce((a, b) => a + b, 0) / 5 / 8) * 10 },
      { k: T.cap, w: 45, have: cap === null ? 0 : 1, of: 1, v: cap === null ? null : cap / 100, earned: cap === null ? 0 : (cap / 100) * 45 },
      { k: T.pres, w: 15, have: pres === null ? 0 : 1, of: 1, v: pres === null ? null : pres / 100, earned: pres === null ? 0 : (pres / 100) * 15 },
    ];
    const wHave = comp.filter((c) => c.v !== null).reduce((a, c) => a + c.w, 0);
    const est = wHave ? comp.filter((c) => c.v !== null).reduce((a, c) => a + c.v * c.w, 0) / wHave * 100 : null;
    const earned = comp.reduce((a, c) => a + c.earned, 0);
    return { comp, est, earned, wHave };
  }
  const band = (x) => x === null ? "—" : x >= 70 ? T.bands[0] : x >= 60 ? T.bands[1] : x >= 50 ? T.bands[2] : T.bands[3];
  function refresh() {
    $$("[data-sprog]").forEach((el) => { const p = sessPct(+el.dataset.sprog); const i = el.querySelector("i"); if (i) i.style.width = p + "%"; const t = el.parentElement.querySelector("[data-sprog-t]"); if (t) t.textContent = p + "%"; });
    $$("[data-overall]").forEach((el) => { const p = overall(); el.style.setProperty("--p", p); const sp = el.querySelector("span"); if (sp) sp.textContent = p + "%"; });
    const capChecks = $$("[data-p^='cap.c']"); const capDone = capChecks.filter((c) => c.checked).length;
    $$("[data-capcount]").forEach((el) => (el.textContent = capChecks.length ? `${capDone}/${capChecks.length}` : ""));
    const g = grade();
    $$("[data-grade-est]").forEach((el) => (el.textContent = g.est === null ? "—" : g.est.toFixed(1)));
    $$("[data-grade-band]").forEach((el) => (el.textContent = band(g.est)));
    $$("[data-grade-earned]").forEach((el) => (el.textContent = g.earned.toFixed(1)));
    const tb = $("#grade-breakdown");
    if (tb) tb.innerHTML = g.comp.map((c) => `<tr><td>${c.k}</td><td class="c">${c.w}%</td><td class="c">${c.have}/${c.of}</td><td class="c">${c.v === null ? "—" : (c.v * 100).toFixed(0) + "%"}</td><td class="c">${c.earned.toFixed(1)}</td></tr>`).join("");
    $$("[data-updated]").forEach((el) => (el.textContent = state._updated ? new Date(state._updated).toLocaleString(T.locale) : T.none));
  }
  bind(); refresh();

  // xuất / nhập / xóa
  $("#prog-export")?.addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = T.exportName + new Date().toISOString().slice(0, 10) + ".json"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  $("#prog-import")?.addEventListener("change", (e) => {
    const f = e.target.files[0]; if (!f) return;
    f.text().then((t) => { try { const d = JSON.parse(t); if (typeof d !== "object") throw 0; state = d; save(); bind(); alertBox(T.imported); } catch (err) { alertBox(T.badFile); } });
  });
  $("#prog-reset")?.addEventListener("click", () => {
    const b = $("#prog-reset");
    if (b.dataset.confirm !== "1") { b.dataset.confirm = "1"; b.textContent = T.confirm; setTimeout(() => { b.dataset.confirm = ""; b.textContent = T.reset; }, 4000); return; }
    state = {}; ls.del(KEY); save(); bind(); b.dataset.confirm = ""; b.textContent = T.reset; alertBox(T.cleared);
  });
  function alertBox(msg) { const el = $("#prog-msg"); if (el) { el.textContent = msg; setTimeout(() => (el.textContent = ""), 4000); } }

  // đánh dấu menu hiện tại
  const here = location.pathname.split("/").pop() || "index.html";
  $$("#nav a").forEach((a) => { const h = a.getAttribute("href"); if (h === here || (here.startsWith("buoi-") && h === "lich-hoc.html")) a.classList.add("active"); });
  window.ERX = { state: () => state, sessionDate, labUrl, lang: LANG };
})();
