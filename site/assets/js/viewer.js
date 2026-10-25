/* PDF viewer (slides & documents) using the pdf.js copy bundled in assets/vendor.
   Document paths ("files/...pdf") are relative to the module root, so the same links work
   from the vi/ and en/ pages and when the module is mounted under any sub-path. */
(function () {
  "use strict";
  if (!window.pdfjsLib) return;
  const ME = document.currentScript || document.querySelector('script[src$="assets/js/viewer.js"]');
  const ROOT = new URL("../../", ME ? ME.src : location.href);           // <module root>/
  pdfjsLib.GlobalWorkerOptions.workerSrc = new URL("assets/vendor/pdf.worker.min.js", ROOT).href;
  const EN = (document.documentElement.lang || "").toLowerCase().startsWith("en");
  const T = EN ? { bad: "Could not open the document.", loading: "Loading…", fail: "Could not load the document. Please use the Download button.", page: "Page " }
               : { bad: "Không mở được tài liệu.", loading: "Đang tải…", fail: "Không tải được tài liệu. Hãy dùng nút Tải về.", page: "Trang " };

  function safeSrc(s) { return /^files\/[\w\-./]+\.pdf$/.test(s || "") && !s.includes("..") ? new URL(s, ROOT).href : null; }

  class Viewer {
    constructor(el) {
      this.el = el; this.src = safeSrc(el.dataset.src); this.page = Math.max(1, parseInt(el.dataset.page || "1", 10)); this.doc = null; this.busy = false; this.queued = null;
      this.canvas = el.querySelector("canvas"); this.count = el.querySelector(".count"); this.input = el.querySelector("input.pg");
      el.querySelector("[data-act=prev]")?.addEventListener("click", () => this.go(this.page - 1));
      el.querySelector("[data-act=next]")?.addEventListener("click", () => this.go(this.page + 1));
      el.querySelector(".hit.l")?.addEventListener("click", () => this.go(this.page - 1));
      el.querySelector(".hit.r")?.addEventListener("click", () => this.go(this.page + 1));
      el.querySelector("[data-act=fs]")?.addEventListener("click", () => this.fullscreen());
      this.input?.addEventListener("change", () => this.go(parseInt(this.input.value, 10) || 1));
      el.tabIndex = 0;
      el.addEventListener("keydown", (e) => this.key(e));
      let t; window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => this.render(), 150); });
      document.addEventListener("fullscreenchange", () => setTimeout(() => this.render(), 60));
      if (!this.src) { this.msg(T.bad); return; }
      const io = new IntersectionObserver((ents) => { if (ents.some((x) => x.isIntersecting)) { io.disconnect(); this.open(); } }, { rootMargin: "200px" });
      io.observe(el);
    }
    msg(t) { const l = this.el.querySelector(".loading"); if (l) { l.textContent = t; l.hidden = false; } }
    async open() {
      this.msg(T.loading);
      try {
        this.doc = await pdfjsLib.getDocument({ url: this.src }).promise;
        this.el.querySelector(".loading").hidden = true;
        const h = /#(?:slide|trang)-(\d+)/.exec(location.hash);
        if (h && this.el.dataset.hash === "1") this.page = +h[1];
        this.go(this.page);
      } catch (e) { this.msg(T.fail); }
    }
    go(n) {
      if (!this.doc) return;
      this.page = Math.min(Math.max(1, n), this.doc.numPages);
      if (this.input) { this.input.value = this.page; this.input.max = this.doc.numPages; }
      if (this.count) this.count.textContent = `${this.page} / ${this.doc.numPages}`;
      if (this.el.dataset.hash === "1") history.replaceState(null, "", "#" + (this.el.dataset.mode === "doc" ? "trang-" : "slide-") + this.page);
      this.render();
    }
    async render() {
      if (!this.doc) return;
      if (this.busy) { this.queued = true; return; }
      this.busy = true;
      try {
        const pg = await this.doc.getPage(this.page);
        const stage = this.canvas.parentElement;
        const fs = document.fullscreenElement === this.el;
        const v1 = pg.getViewport({ scale: 1 });
        let w = stage.clientWidth;
        if (fs) w = Math.min(w, (window.innerHeight - 64) * (v1.width / v1.height));
        if (this.el.dataset.mode === "doc" && !fs) w = Math.min(w, 900);
        const scale = w / v1.width; const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
        const vp = pg.getViewport({ scale: scale * dpr });
        this.canvas.width = Math.floor(vp.width); this.canvas.height = Math.floor(vp.height);
        this.canvas.style.width = Math.floor(vp.width / dpr) + "px";
        await pg.render({ canvasContext: this.canvas.getContext("2d"), viewport: vp }).promise;
        this.canvas.setAttribute("aria-label", T.page + this.page);
      } catch (e) { /* bỏ qua lỗi render tạm thời */ }
      this.busy = false;
      if (this.queued) { this.queued = false; this.render(); }
    }
    key(e) {
      if (e.target.tagName === "INPUT") return;
      if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); this.go(this.page + 1); }
      if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); this.go(this.page - 1); }
      if (e.key === "Home") this.go(1);
      if (e.key === "End" && this.doc) this.go(this.doc.numPages);
      if (e.key === "f") this.fullscreen();
    }
    fullscreen() {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (this.el.requestFullscreen) this.el.requestFullscreen().catch(() => {});
      this.el.focus();
    }
  }

  // xem.html?f=files/docs/x.pdf&p=12&t=Tiêu đề
  const solo = document.getElementById("doc-viewer");
  if (solo) {
    const q = new URLSearchParams(location.search);
    const f = safeSrc(q.get("f"));
    if (f) {
      solo.dataset.src = q.get("f"); solo.dataset.page = q.get("p") || "1";
      const t = q.get("t"); if (t) { document.getElementById("doc-title").textContent = t; document.title = t + " · ERX"; }
      const dl = document.getElementById("doc-dl"); if (dl) dl.href = f;
    }
  }
  document.querySelectorAll(".viewer[data-src]").forEach((el) => new Viewer(el));
})();
